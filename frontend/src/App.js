// App.js - Single-page dashboard: filters, metric cards, charts.
// Fetches /api/wind-analysis from the FastAPI backend (URL from REACT_APP_API_URL).
import { useEffect, useState } from "react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Wind } from "lucide-react";

const API = (process.env.REACT_APP_API_URL || "http://localhost:8000").replace(/\/+$/, "");
const fmt = (v, d = 0) => (v == null ? "-" : Number(v).toLocaleString("en-GB", { maximumFractionDigits: d }));

function Card({ label, value, unit, hint }) {
  return (
    <div className="card">
      <div className="label">{label}</div>
      <div className="value">{value}<span style={{ fontSize: 13 }}> {unit}</span></div>
      <div className="hint">{hint}</div>
    </div>
  );
}

export default function App() {
  const [start, setStart] = useState("2026-01-01");
  const [end, setEnd] = useState("2026-01-31");
  const [cutoff, setCutoff] = useState(9);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (start > end) { setErr("Start date must be before end date"); return; }
    setLoading(true); setErr("");
    fetch(`${API}/api/wind-analysis?start=${start}&end=${end}&cutoff_hour=${cutoff}`)
      .then(r => r.ok ? r.json() : r.json().then(j => Promise.reject(j.detail || "Request failed")))
      .then(setData)
      .catch(e => setErr(String(e)))
      .finally(() => setLoading(false));
  }, [start, end, cutoff]);

  const m = data?.metrics;
  const series = (data?.series || []).map(s => ({ ...s, label: s.t.slice(5, 16).replace("T", " ") }));

  return (
    <div className="container">
      <h1><Wind size={22} style={{ verticalAlign: "-3px" }} /> UK Wind Forecast Accuracy</h1>
      <p className="sub">Day-ahead decision support, national wind generation (Elexon BMRS), January 2026</p>

      <div className="controls">
        <label>From<input type="date" min="2026-01-01" max="2026-01-31" value={start} onChange={e => setStart(e.target.value)} /></label>
        <label>To<input type="date" min="2026-01-01" max="2026-01-31" value={end} onChange={e => setEnd(e.target.value)} /></label>
        <label>Decision cutoff on D-1 (UTC)
          <select value={cutoff} onChange={e => setCutoff(Number(e.target.value))}>
            {[6, 7, 8, 9, 10, 11, 12].map(h => <option key={h} value={h}>{String(h).padStart(2, "0")}:00</option>)}
          </select>
        </label>
      </div>

      {err && <p className="error">{err}</p>}
      {loading && <p>Loading…</p>}

      {m && m.n > 0 && (
        <>
          <div className="note">
            For each half-hour, the forecast used is the <b>latest one published on or before {String(cutoff).padStart(2, "0")}:00 on the previous day</b> -
            the information a buyer actually has when bidding in the day-ahead market. Error = forecast − actual (positive = wind over-forecast).
          </div>
          <div className="cards">
            <Card label="MAE" value={fmt(m.mae_mw)} unit="MW" hint="Average absolute error" />
            <Card label="RMSE" value={fmt(m.rmse_mw)} unit="MW" hint="Penalises large misses" />
            <Card label="Bias" value={fmt(m.bias_mw)} unit="MW" hint={m.bias_mw > 0 ? "Forecasts run high on average" : "Forecasts run low on average"} />
            <Card label="WAPE" value={fmt(m.wape_pct, 1)} unit="%" hint="Total abs error / total actual" />
            <Card label="P90 over-forecast" value={fmt(m.p90_overforecast_mw)} unit="MW" hint="Suggested thermal buffer (90% cover)" />
            <Card label="Half-hours" value={fmt(m.n)} unit="" hint="Data points evaluated" />
          </div>

          <div className="panel">
            <h2>Actual vs forecast generation (MW)</h2>
            <ResponsiveContainer width="100%" height={340}>
              <LineChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e3e8ef" />
                <XAxis dataKey="label" minTickGap={60} fontSize={11} />
                <YAxis fontSize={11} />
                <Tooltip /><Legend />
                <Line type="monotone" dataKey="actual" name="Actual" stroke="#059669" dot={false} strokeWidth={1.5} />
                <Line type="monotone" dataKey="forecast" name="Forecast (at cutoff)" stroke="#1d4ed8" dot={false} strokeWidth={1.5} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="panel">
            <h2>Forecast error over time (MW, forecast − actual)</h2>
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={series}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e3e8ef" />
                <XAxis dataKey="label" minTickGap={60} fontSize={11} />
                <YAxis fontSize={11} /><Tooltip />
                <Line type="monotone" dataKey="error" name="Error" stroke="#dc2626" dot={false} strokeWidth={1} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="panel">
            <h2>Mean absolute error by hour of day (MW)</h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data.by_hour}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e3e8ef" />
                <XAxis dataKey="hour" fontSize={11} /><YAxis fontSize={11} /><Tooltip />
                <Bar dataKey="mae_mw" name="MAE" fill="#1d4ed8" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  );
}
