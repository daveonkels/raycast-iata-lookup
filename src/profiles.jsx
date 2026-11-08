import sources from "../assets/sources.json";
import { useMemo } from "react";
import { Action, ActionPanel, Detail, environment } from "@raycast/api";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const cache = new Map();
function profiles(kind) {
  if (!cache.has(kind)) {
    const file = join(environment.assetsPath, kind.toLowerCase() + "-profiles.json");
    cache.set(kind, JSON.parse(readFileSync(file, "utf8")));
  }
  return cache.get(kind);
}
const md = value => String(value ?? "").replace(/[\r\n]+/g, " ").replace(/[\\`*_{}\[\]()<>#!|]/g, "\\$&");
const fmt = n => Number(n).toLocaleString("en-US", {maximumFractionDigits: 1});

function Profile({ row, markdown, labels, icao, callsign }) {
  return <Detail navigationTitle={row.code + " / " + row.kind} markdown={markdown}
    metadata={<Detail.Metadata>
      {labels.filter(([,value]) => value).map(([title,value]) =>
        <Detail.Metadata.Label key={title} title={title} text={String(value)} />)}
    </Detail.Metadata>}
    actions={<ActionPanel>
      <Action.CopyToClipboard title="Copy IATA Code" content={row.code} />
      {icao && <Action.CopyToClipboard title="Copy ICAO Code" content={icao}/>}
      {callsign && <Action.CopyToClipboard title="Copy Callsign" content={callsign}/>}
      <Action.CopyToClipboard title="Copy Name" content={row.name}/>
    </ActionPanel>} />;
}

export function AirlineDetail({row}) {
  const f = profiles("Airline")[row.id] || {};
  const parts = ["# " + md(row.name), "## Flight identification"];
  const ids = ["**On the ticket**　" + md(row.code) + "123"];
  if (f.icao) ids.push("**On a flight plan**　" + md(f.icao) + "123");
  if (f.callsign) ids.push("**On the radio**　" + md(f.callsign) + " ONE TWO THREE");
  parts.push(ids.join("  \n"), "Example flight number 123.");
  if (f.network) {
    const {airports,pairs,top} = f.network;
    parts.push("## Route archive · " + sources.openflights.routeArchive,
      "**" + fmt(airports) + " airports** linked by **" + fmt(pairs) + " nonstop airport pairs** in the archive. Each pair counts once in either direction. Codeshares are excluded.",
      "### Most nonstop connections",
      top.map(a => "**" + md(a.code || a.name) + "**　" + (a.code ? md(a.name) + " · " : "") + fmt(a.count) + (a.count === 1 ? " connection" : " connections")).join("\n\n"));
  }
  if (!f.directory) parts.push("Only the booking identity is confirmed in the offline carrier directory.");
  const labels = [["IATA airline code",row.code],["ICAO operator",f.icao],["Radio callsign",f.callsign],
    ["Country",f.country],["Also listed as",f.alias],["Carriage terms host",f.termsHost],
    ["Duffel catalog",sources.duffel.date], ["Directory",f.directory ? "Duffel · OpenFlights" : "Duffel"]];
  return <Profile row={row} markdown={parts.join("\n\n")} labels={labels} icao={f.icao} callsign={f.callsign}/>;
}

export function AircraftDetail({row, catalog}) {
  const data = profiles("Aircraft");
  const f = data[row.id] || {};
  const spec = f.faa;
  const related = useMemo(() => f.family ? catalog.filter(({row: other}) =>
    other.kind === "Aircraft" && other.id !== row.id && data[other.id]?.family === f.family
  ).slice(0,3).map(entry => entry.row) : [], [data, f.family, row.id, catalog]);
  const parts = ["# " + md(row.name)];
  const surface = row.name.startsWith("Surface Equipment");
  if (spec) {
    parts.push("## Airframe", "**FAA reference model**　" + md(spec.reference));
    const dimensions = [["Length",spec.length],["Wingspan without winglets",spec.span],
      ["Wingspan with winglets",spec.spanTips],["Tail height at operating empty weight",spec.height],["Rotor diameter",spec.rotor]];
    const lines = dimensions.filter(([,n]) => n).map(([k,n]) => "**"+k+"**　"+fmt(n)+" ft / "+fmt(n*0.3048)+" m");
    if (lines.length) parts.push(lines.join("  \n"));
    const weights = [["Max takeoff",spec.mtow],["Max landing",spec.landing]].filter(([,n])=>n);
    if (weights.length) parts.push("## Design weights", weights.map(([k,n]) =>
      "**"+k+"**　"+fmt(Math.round(n))+" lb / "+fmt(Math.round(n*0.45359237))+" kg").join("  \n"));
  } else {
    parts.push("## Equipment identification", surface ? "Airline schedules use **"+md(row.code)+"** for this surface transport segment."
      : "**"+md(row.code)+"** identifies "+md(row.name)+" in airline schedules.");
    if (!surface) parts.push("The offline FAA reference has no unambiguous specification for this entry.");
  }
  if (related.length) parts.push("## Other " + md(f.family) + " equipment codes",
    related.map(r => "**"+md(r.code)+"**　"+md(r.name)).join("  \n"));
  const engine = spec?.engine && (spec.engines ? spec.engines + " × " : "") + spec.engine;
  const labels = [["IATA equipment",row.code],["ICAO type",f.icao],["Family",f.family],
    ["Manufacturer",spec?.maker],["Class",spec?.category],["Powerplants",engine],
    ["Wake category",spec?.wake],["Specifications",spec && "FAA ACD · " + sources.faa.edition],
    ["Duffel catalog", sources.duffel.date]];
  return <Profile row={row} markdown={parts.join("\n\n")} labels={labels} icao={f.icao}/>;
}
