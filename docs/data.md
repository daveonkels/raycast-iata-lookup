# Offline data

| Source | What it contributes |
| --- | --- |
| [Duffel snapshot in Tim Rogers’s IATA Code Decoder API](https://github.com/timrogers/iata-code-decoder-api/tree/a9bb73cde38a02d07a4d764d7ce7a742dba4b8b6/data) | Booking codes, display names, airport identifiers, locations, and time zones. The [upstream MIT notice](../assets/UPSTREAM-LICENSE.txt) is included. |
| [OurAirports snapshot](https://github.com/davidmegginson/ourairports-data/tree/bdbcf5e2643119210d5c240f2e26ab2604ec5e38) | Airfields, runways, communications, regions, and associated navaids. OurAirports publishes these files in the [public domain](https://ourairports.com/data/). |
| [OpenFlights snapshot](https://github.com/jpatokal/openflights/tree/115067fd23d1221f93edfda3701a69e106672953/data) | Airline directory, equipment designators, and historical route summaries. The June 2014 route archive counts an airport pair once in either direction and excludes marked codeshares and multistop routes. The derived profile data is available under [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/) with individual contents under [DbCL 1.0](https://opendatacommons.org/licenses/dbcl/1-0/). |
| [FAA Aircraft Characteristics Database](https://www.faa.gov/airports/engineering/aircraft_char_database) | October 2024 workbook. Dimensions, weights, and classifications describe the matched reference model. |

## Rebuild the snapshots

The command reads the checked-in JSON directly. To regenerate the files, run the following from the repository root with Python 3. The profile builder also requires an environment with `openpyxl` installed.

1. Set `DUFFEL_DATA` to the upstream snapshot’s `data` directory.
2. Set `OURAIRPORTS_DATA` to a directory containing `airports.csv`, `regions.csv`, `runways.csv`, `airport-frequencies.csv`, and `navaids.csv`.
3. Set `PROFILE_DATA` to a directory containing OpenFlights’ `airlines.dat`, `airports.dat`, `planes.dat`, and `routes.dat`, plus the October 2024 FAA workbook named `faa.xlsx`.

```sh
python3 tools/prepare-catalog.py "$DUFFEL_DATA"
python3 tools/prepare-airfields.py "$OURAIRPORTS_DATA" "$DUFFEL_DATA"
python3 tools/prepare-profiles.py "$PROFILE_DATA" "$DUFFEL_DATA"
```

The builders write to `assets/`. Review the data diff before shipping a new snapshot.
