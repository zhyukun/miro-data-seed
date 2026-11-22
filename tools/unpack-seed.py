#!/usr/bin/env python3
"""Print the APFS volume UUIDs of a packed DarwinBoot Data seed (.dbr).

The packed form is what payload.py wants; the kernel compares the Data volume
UUID against CONFIG_XNU_OWNER_DATA_VOLUME_UUID, so the value has to come out of
the seed that was actually built. Two independent readings are printed: the
volume superblock (APSB) parsed straight out of the seed, and what diskutil
reports for the attached raw image.
"""
import json
import os
import plistlib
import struct
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

search = [Path(os.environ.get('UNIXNU_DIR', 'unixnu')), Path('unixnu'), Path('.').resolve()]
for candidate in search:
    module = candidate / 'drivers/DarwinBoot/Test'
    if (module / 'packed_ramdisk.py').is_file():
        sys.path.insert(0, str(module.resolve()))
        break
else:
    sys.exit('packed_ramdisk.py not found: set UNIXNU_DIR to the UniXNU checkout')

import packed_ramdisk

PAGE = 4096
VOL_UUID_OFFSET = 0xf0        # apfs_superblock: apfs_vol_uuid, right after the seven block/file counters
VOL_NAME_OFFSET = 0x2c0       # apfs_superblock: apfs_volname


def parse_volumes(logical, extents):
    volumes = []
    for offset, data in extents:
        for at in range(0, len(data) - PAGE + 1, PAGE):
            page = bytes(data[at:at + PAGE])
            if page[32:36] != b'APSB':
                continue
            name = page[VOL_NAME_OFFSET:VOL_NAME_OFFSET + 256].split(b'\x00')[0].decode('utf-8', 'replace')
            volumes.append({'at': hex(offset + at), 'name': name,
                            'volume_uuid': str(uuid.UUID(bytes=page[VOL_UUID_OFFSET:VOL_UUID_OFFSET + 16]))})
    return volumes


def diskutil_volumes(raw):
    attached = plistlib.loads(subprocess.check_output(
        ['hdiutil', 'attach', '-nomount', '-nobrowse', '-plist',
         '-imagekey', 'diskimage-class=CRawDiskImage', str(raw)]))
    device = attached['system-entities'][0]['dev-entry']
    try:
        listing = plistlib.loads(subprocess.check_output(['diskutil', 'apfs', 'list', '-plist', device]))
        result = []
        for container in listing.get('Containers', []):
            for volume in container.get('Volumes', []):
                result.append({'container_uuid': container.get('APFSContainerUUID'),
                               'name': volume.get('Name'), 'volume_uuid': volume.get('APFSVolumeUUID')})
        return result
    finally:
        subprocess.run(['hdiutil', 'detach', device, '-force'], capture_output=True, check=False)


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: unpack-seed.py <seed.dbr>')
    blob = Path(sys.argv[1]).read_bytes()
    logical, extents = packed_ramdisk.regions(blob)
    print(json.dumps({'logical_bytes': logical, 'logical_gib': round(logical / 1024**3, 3),
                      'encoded_bytes': len(blob), 'extents': len(extents)}))
    print(json.dumps({'volume_superblocks': parse_volumes(logical, extents)}, indent=2))
    with tempfile.TemporaryDirectory(prefix='seed-probe-') as scratch:
        raw = Path(scratch) / 'seed.raw'
        with raw.open('wb') as handle:
            handle.truncate(logical)
            for offset, data in extents:
                handle.seek(offset)
                handle.write(data)
        try:
            print(json.dumps({'diskutil': diskutil_volumes(raw)}, indent=2))
        except Exception as error:                   # the APSB parse above is authoritative
            print(json.dumps({'diskutil_error': f'{type(error).__name__}: {error}'}))


if __name__ == '__main__':
    main()
