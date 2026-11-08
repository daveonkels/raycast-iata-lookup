import { useMemo, useState } from "react";
import { Action, ActionPanel, Color, Icon, List, environment } from "@raycast/api";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { indexCatalog, search } from "./catalog.mjs";

import AirportDetail from "./airport.jsx";

import { AirlineDetail, AircraftDetail } from "./profiles.jsx";

const icons = {
  Airport: { source: Icon.AirplaneLanding, tintColor: Color.Blue },
  Airline: { source: Icon.Globe, tintColor: Color.Green },
  Aircraft: { source: Icon.Airplane, tintColor: Color.Orange },
};

export default function SearchIata() {
  const [text, setText] = useState("");
  const catalog = useMemo(() => indexCatalog(JSON.parse(
    readFileSync(join(environment.assetsPath, "catalog.json"), "utf8")
  )), []);
  const results = useMemo(() => search(catalog, text), [catalog, text]);
  return (
    <List filtering={false} onSearchTextChange={setText}
          searchBarPlaceholder="Search by code, name, or city…">
      {results.length === 0 && <List.EmptyView icon={Icon.MagnifyingGlass}
        title={text.trim() ? "No matches" : "Find an airport, airline, or aircraft"}
        description={text.trim() ? "Try another code, name, or city." : "Try RST, B6, or 738."} />}
      {results.map(row => (
        <List.Item key={row.id} id={row.id} icon={icons[row.kind]}
          title={row.code} subtitle={row.name}
          accessories={[{ text: [row.city, row.country].filter(Boolean).join(", ") || row.kind,
            tooltip: [row.kind, row.icao, row.zone].filter(Boolean).join(" · ") }]}
          actions={<ActionPanel>
            {row.kind === "Airport" && <Action.Push title="Open Airport Briefing" icon={Icon.AirplaneLanding} target={<AirportDetail row={row} />} />}
            {row.kind === "Airline" && <Action.Push title="Open Airline Profile" icon={Icon.Globe} target={<AirlineDetail row={row} />} />}
            {row.kind === "Aircraft" && <Action.Push title="Open Aircraft Profile" icon={Icon.Airplane} target={<AircraftDetail row={row} catalog={catalog} />} />}
            <Action.CopyToClipboard title="Copy Code" content={row.code} />
            <Action.CopyToClipboard title="Copy Name" content={row.name} />
            {row.icao && <Action.CopyToClipboard title="Copy ICAO Code" content={row.icao} />}
          </ActionPanel>} />
      ))}
    </List>
  );
}
