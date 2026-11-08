# IATA Lookup for Raycast

Type `RST` to see Rochester’s runways and tower frequency, `B6` to see how a JetBlue flight would identify itself on the radio, or `738` to look up the Boeing 737-800’s wingspan. IATA Lookup searches 9,045 airports, 787 airlines, and 525 aircraft and equipment entries. All lookups run on your Mac using the bundled data.

![Rochester International Airport briefing with a north-up runway diagram and field information](docs/screenshots/airport.png)

## Search

Open **Search IATA Codes** in Raycast and type a booking code, airport ICAO code, name, or city. The list updates with each keystroke and shows up to three matches. An exact code takes priority. Press **Return** to open a result, **⌘K** for copy actions, or **Esc** to go back.

![Searching for London in Raycast with three matching airports](docs/screenshots/search.png)

## Explore a result

**Airports** show runway dimensions, surfaces and lighting, radio frequencies, associated navigation aids, elevation, coordinates, and time zone where available. The extension draws its north-up runway diagrams locally from published runway endpoints. For aviation reference only. Use current official charts for navigation.

**Airlines** show how the booking code, ICAO operator code, and spoken callsign fit together. Where available, the June 2014 OpenFlights archive shows the carrier’s busiest stations by number of distinct nonstop connections.

![JetBlue Airways with ticket, flight plan and radio identifiers and its archived route network](docs/screenshots/airline.png)

**Aircraft** show the IATA equipment code, ICAO type, and related variants. Unambiguous FAA reference models also include available dimensions, engine details, wake category, and design weights in US and metric units.

![Boeing 737-800 aircraft profile with dimensions, design weights and engine details](docs/screenshots/aircraft.png)

## Run locally

You’ll need Raycast for macOS, Git, Node.js 22.14 or later, and an existing Raycast SDK CLI (`ray`). The CLI comes with `@raycast/api`. If you already develop Raycast extensions, you can use the full path to an existing project’s `node_modules/.bin/ray` in place of `ray`. [Raycast developer guide](https://developers.raycast.com/basics/getting-started)

```sh
git clone https://github.com/daveonkels/raycast-iata-lookup.git
cd raycast-iata-lookup
ray develop
```

Open Raycast and search for **Search IATA Codes**. The development command watches for edits. To build the extension bundle into a local directory, run `ray build -e dist -o dist`. The repository includes all lookup data and requires no API key or background service.

## Data and license

The extension code is [MIT licensed](LICENSE). The booking catalog comes from a Duffel snapshot. Airfield data comes from OurAirports, airline and equipment records from OpenFlights, and aircraft specifications from the FAA. Coverage varies by record. The bundled data carries its source terms, including ODbL 1.0 for OpenFlights-derived profile data. [Source revisions and rebuild instructions](docs/data.md) · [Bundled attribution](assets/PROFILE-SOURCES.txt)
