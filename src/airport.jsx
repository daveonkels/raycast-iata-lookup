import sources from "../assets/sources.json";
import { useMemo } from "react";
import { Action, ActionPanel, Detail, environment } from "@raycast/api";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { diagram } from "./runway-diagram.mjs";

const surfaceNames = { CON: "Concrete", CONC: "Concrete", ASP: "Asphalt", ASPH: "Asphalt",
  GRS: "Grass", TURF: "Turf", GVL: "Gravel" };
const md = s => String(s ?? "").replace(/[\r\n]+/g, " ").replace(/[\\`*_{}\[\]()<>#!|]/g, "\\$&");
const feet = value => Number(value).toLocaleString("en-US") + " ft";
const heading = value => String(Math.round(Number(value)) % 360).padStart(3, "0") + "°T";
const coord = (value, positive, negative) => Math.abs(value).toFixed(4) + "° " + (value >= 0 ? positive : negative);

function runwayText(r) {
  const ends = [r.le_ident, r.he_ident].filter(Boolean);
  const name = ends.length ? ends.join(" / ") : "Unnumbered";
  const size = r.length_ft && r.width_ft ? Number(r.length_ft).toLocaleString("en-US") + " × " + feet(r.width_ft)
    : r.length_ft ? feet(r.length_ft) + " long" : r.width_ft ? feet(r.width_ft) + " wide" : "";
  const specs = [size, surfaceNames[r.surface?.toUpperCase()] || r.surface, r.lighted === "1" && "Lighted"].filter(Boolean);
  const lines = ["### " + md(name) + (r.closed === "1" ? " · CLOSED" : ""), md(specs.join(" · "))];
  for (const end of ["le", "he"]) {
    const id = r[end+"_ident"], bearing = r[end+"_heading_degT"], elev = r[end+"_elevation_ft"], offset = r[end+"_displaced_threshold_ft"];
    const facts = [bearing && heading(bearing), elev && feet(elev) + " end elevation",
      Number(offset) > 0 && feet(offset) + " displaced threshold"].filter(Boolean);
    if (id && facts.length) lines.push("**" + md(id) + "**  " + md(facts.join(" · ")));
  }
  return lines.filter(Boolean).join("  \n");
}

function briefing(row, field) {
  const runs = field.runways || [], radios = field.radios || [], aids = field.navaids || [];
  const blocks = ["# " + md(row.name), "Reference only · Not for navigation"];
  const image = diagram(runs, field.lat, field.lon);
  if (image) blocks.push("![North-up runway schematic](" + image + ")");
  if (runs.length) blocks.push("## Runways", ...runs.map(runwayText));
  if (radios.length) blocks.push("## Communications", radios.map(r => {
    const name = [r.type, r.description && r.description !== r.type ? r.description : null].filter(Boolean).join(" · ");
    return "**" + md(name) + "**　" + (r.frequency_mhz ? md(r.frequency_mhz) + " MHz" : "Frequency unlisted");
  }).join("  \n"));
  if (aids.length) blocks.push("## Associated navaids", aids.map(a => {
    const freq = a.frequency_khz ? Number(a.frequency_khz) >= 100000 ? Number(a.frequency_khz)/1000 + " MHz" : a.frequency_khz + " kHz" : "";
    return "**" + md([a.ident,a.type].filter(Boolean).join(" · ")) + "**　" + md([a.name, freq, a.dme_channel && "DME " + a.dme_channel].filter(Boolean).join(" · "));
  }).join("  \n"));
  if (!runs.length && !radios.length && !aids.length) blocks.push("Runway, radio, and navaid records are unavailable in this snapshot.");
  return blocks.join("\n\n");
}

export default function AirportDetail({row}) {
  const field = useMemo(() => JSON.parse(readFileSync(join(environment.assetsPath, "airfields", row.code[0]+".json"),"utf8"))[row.id], [row]);
  const position = coord(field.lat, "N","S") + " · " + coord(field.lon, "E","W");
  const elevation = field.elevation_ft != null ? feet(field.elevation_ft) + " MSL" : null;
  const labels = [
    ["IATA",row.code],["ICAO",row.icao],["Local ID",field.local_code],
    ["Location",[row.city,field.region,row.country].filter(Boolean).join(", ")],
    ["Field elevation",elevation],["Latitude",coord(field.lat,"N","S")],["Longitude",coord(field.lon,"E","W")],
    ["Time zone",row.zone],["Airfield type",field.type?.replace(/_/g," ")],
    ["Scheduled service",field.scheduled_service],["Source",field.type ? "OurAirports · Duffel" : "Duffel"],
    ["Booking catalog", sources.duffel.date], ["Airfield data", field.type && sources.ourairports.date]
  ];
  return <Detail navigationTitle={[row.icao,row.code].filter(Boolean).join(" / ")} markdown={briefing(row, field)}
    metadata={<Detail.Metadata>{labels.filter(([,value]) => value).map(([title,text]) =>
      <Detail.Metadata.Label key={title} title={title} text={text} />)}</Detail.Metadata>}
    actions={<ActionPanel><Action.CopyToClipboard title="Copy Airport Code" content={row.code} />
      {row.icao && <Action.CopyToClipboard title="Copy ICAO Code" content={row.icao}/>}
      <Action.CopyToClipboard title="Copy Coordinates" content={position} />
      <Action.CopyToClipboard title="Copy Airport Name" content={row.name}/>
    </ActionPanel>} />;
}
