#!/usr/bin/env python3
"""Print the APFS volume UUIDs of a packed DarwinBoot Data seed (.dbr).

The packed form is what payload.py wants; the kernel compares the Data volume
UUID against CONFIG_XNU_OWNER_DATA_VOLUME_UUID, so the value has to come out of
the seed that was actually built.
"""
import json
import plistlib
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'unixnu/drivers/DarwinBoot/Test'))
import packed_ramdisk


def main():
    if len(sys.argv) != 2:
        sys.exit('usage: unpack-seed.py <seed.dbr>')
    blob = Path(sys.argv[1]).read_bytes()
    logical, extents = packed_ramdisk.regions(blob)
    print(json.dumps({'logical_bytes': logical, 'logical_gib': round(logical / 1024**3, 3)}))
    with tempfile.TemporaryDirectory(prefix='seed-probe-') as scratch:
        raw = Path(scratch) / 'seed.raw'
        with raw.open('wb') as handle:
            handle.truncate(logical)
            for offset, data in extents:
                handle.seek(offset)
                handle.write(data)
        attached = plistlib.loads(subprocess.check_output(
            ['hdiutil', 'attach', '-nomount', '-nobrowse', '-plist', str(raw)]))
        device = attached['system-entities'][0]['dev-entry']
        try:
            listing = plistlib.loads(subprocess.check_output(
                ['diskutil', 'apfs', 'list', '-plist', device]))
            for container in listing.get('Containers', []):
                print(json.dumps({'container_uuid': container.get('APFSContainerUUID')}))
                for volume in container.get('Volumes', []):
                    print(json.dumps({'volume_name': volume.get('Name'),
                                      'volume_uuid': volume.get('APFSVolumeUUID')}))
        finally:
            subprocess.run(['hdiutil', 'detach', device, '-force'], capture_output=True, check=False)


if __name__ == '__main__':
    main()
