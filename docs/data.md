# Maintaining the offline snapshot

The [source manifest](../assets/sources.json) records the revision and file hashes used for each GitHub dataset, the FAA workbook edition and checksum, and the period covered by the route archive. The detail views read their dates from this manifest. A revision date identifies a snapshot, not the date each field was independently verified.

| Source | Inputs and update policy |
| --- | --- |
| [Duffel via Tim Rogers’s repository](https://github.com/timrogers/iata-code-decoder-api/tree/main/data) | Booking identifiers, names, airport locations and time zones. The job checks the latest change under `data/`. The [upstream MIT notice](../assets/UPSTREAM-LICENSE.txt) is bundled. |
| [OurAirports](https://ourairports.com/data/) | Public-domain airports, runways, frequencies, navaids and regions. The job downloads all five CSVs at one commit. An airfield match requires compatible identifiers, matching country, proximity within 25 km and a single surviving candidate. |
| [OpenFlights](https://openflights.org/data.php) | Carrier and equipment directories plus archived route pairs. The route archive describes June 2014. A change to the route file stops the job until a maintainer confirms the period and updates its hash and label. Derived profiles carry [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) and individual contents carry [DbCL 1.0](https://opendatacommons.org/licenses/dbcl/1-0/). |
| [FAA Aircraft Characteristics Database](https://www.faa.gov/airports/engineering/aircraft_char_database) | The job reads the edition from the FAA publication page and hashes the downloaded workbook. The project retains the exact workbook under `data/` so older commits can be reproduced if the FAA replaces its download. Specifications describe a matched reference model. |

## Review a refresh

GitHub checks at 10:17 UTC on the first of each month. To check now, run `gh workflow run refresh.yml` on the default branch. Open **Actions → Refresh offline data** for the review summary. Unchanged input bytes retain their original pins. A change creates one pull request. If a snapshot is already awaiting review, finish it and dispatch the workflow again to check for newer changes.

1. Read the source revisions and the counts for additions, removals, reassignments, lost coverage and changes to aviation details. To examine a specific airport, compare its entries in the old and new JSON with a JSON viewer. Check consequential runway or frequency changes against the relevant aviation authority’s current publication.
2. Inspect unexpected coverage changes. For a reassigned booking code, verify that the callsign belongs to the new carrier. For changed aircraft dimensions, verify the named FAA variant. Structural checks catch broken references and unusable data. Source corrections and real-world changes still need judgment.
3. Merge the reviewed PR. In the installed extension’s checkout, run `git pull --ff-only` and restart `ray develop`. To withdraw a bad update, revert the snapshot PR and rebuild the installed extension.

## Reproduce or diagnose a run

Use Python 3.10 or newer, Node.js 22 or newer, curl, and the existing Python workbook reader. CI installs the exact wheels listed in `tools/requirements.txt` into a temporary virtual environment. From the repository root, choose a new output directory for each build.

```sh
# Check the installed checkout with no network access.
python3 tools/snapshot.py assets
node tools/check-search.mjs

# Download the recorded GitHub inputs and verify their hashes. Use the retained FAA workbook.
python3 tools/refresh.py --locked /tmp/iata-reproduction

# Discover current editions, build a candidate and write its review.md.
python3 tools/refresh.py /tmp/iata-candidate
```

A failed download, unrecognized FAA edition, or failed check stops publication. See the failing Actions step, fix the source or parser if needed, and rerun the workflow. Each run builds into a temporary directory. The refresh uses the repository’s built-in Actions token to open PRs, and the maintainer merges them. To restore scheduling after GitHub disables it on an inactive public repository, open the workflow in Actions, select **Enable workflow** and run it once manually.
