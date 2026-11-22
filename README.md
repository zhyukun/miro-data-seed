# miro-data-seed

Builds the **first-install APFS Data seed** (`.dbr`) that the [UniXNU](https://github.com/UniXNU/UniXNU)
port of the Redmi K80 Pro needs, on a GitHub macOS runner, because `make-data-seed.py`
depends on `hdiutil` and `diskutil` and there is no Linux equivalent.

Upstream only *accepts* a seed (`data_seed_url`) and can grow one; it never creates one. This
repository fills that gap: it downloads the stock IPSW, attaches its OS image, calls
`scripts/make-data-seed.py`, reads the resulting APFS volume UUID with `tools/unpack-seed.py`,
and commits both back to `data/`.

## Why the UUID matters

The kernel compares the Data volume UUID with `CONFIG_XNU_OWNER_DATA_VOLUME_UUID` in the device
defconfig. A seed built here gets a fresh random UUID, so the defconfig has to be rebuilt with the
value this run prints — otherwise the volume is published but never matched.

## Output

| Path | Contents |
| --- | --- |
| `data/data-seed.dbr` | The packed seed (`DBRDISK1`), the form `unixnu build payload --data-ramdisk` takes |
| `data/data-seed-uuid.txt` | Logical size, container UUID and the Data volume UUID |

## Reproducing

Run the **iPadOS Data seed** workflow (`workflow_dispatch`), or push any non-`data/` change.
Defaults: iPadOS 17.7.11 / 21H461, OS image `044-76040-038.dmg`, 8 GiB Data volume.

Public repository on purpose: macOS runner minutes are not billed on public repositories.
No secret and no key material is involved — the seed is generic installation state taken from a
stock Apple image.
