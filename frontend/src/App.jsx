import { useState } from "react";
import { Routes, Route } from "react-router-dom";
import Emergency from "./Emergency";

const API = "https://veterinary-practice-manager.onrender.com";

function Home() {
  const [petName, setPetName] = useState("");
  const [note, setNote] = useState("");
  const [status, setStatus] = useState({ msg: "", type: "" }); // Improved status handling
  const [protocols, setProtocols] = useState([]);
  const [qrUrl, setQrUrl] = useState("");

  const saveRecord = async () => {
    setStatus({ msg: "Saving record...", type: "loading" });
    try {
      const res = await fetch(`${API}/add-record`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ pet_name: petName, note }),
      });
      if (res.ok)
        setStatus({
          msg: "✅ Medical record saved successfully",
          type: "success",
        });
      else throw new Error();
    } catch {
      setStatus({ msg: "❌ Error saving record", type: "error" });
    }
  };

  const suggestProtocol = async () => {
    // 🔥 CLEAR OLD RESULTS FIRST
    setProtocols([]);

    setStatus({ msg: "🤖 AI Analyzing...", type: "loading" });

    try {
      const res = await fetch(
        `${API}/suggest-protocol?note=${encodeURIComponent(note)}`,
        { method: "POST" },
      );
      const data = await res.json();

      setProtocols(data); // ✅ New results only
      setStatus({ msg: "✅ Protocols generated", type: "success" });
    } catch {
      setStatus({ msg: "❌ AI Analysis Failed", type: "error" });
    }
  };

  const generateQR = () => {
    if (!petName) return alert("Please enter a pet name");
    setQrUrl(`${API}/qr/${petName}`);
  };

  return (
    <div className="container">
      <header className="header">
        <h1>🐾 Vet Practice Manager</h1>
        <p className="subtitle">AI-assisted records & Emergency Response</p>
      </header>

      <div className="card">
        <h2>Patient Intake</h2>

        <div className="form-group">
          <label>Pet Name</label>
          <input
            value={petName}
            onChange={(e) => {
              setPetName(e.target.value);
              setQrUrl(""); // 🔥 clear QR
            }}
            placeholder="e.g. Luna"
          />
        </div>

        <div className="form-group">
          <label>Clinical Notes / Symptoms</label>
          <textarea
            rows="5"
            value={note}
            onChange={(e) => {
              setNote(e.target.value);
              setProtocols([]); // clear AI results
              setQrUrl(""); // 🔥 clear QR
            }}
            placeholder="Describe symptoms, vital signs, or diagnosis..."
          />
        </div>

        <div className="buttons">
          <button className="btn-primary" onClick={saveRecord}>
            💾 Save Record
          </button>
          <button className="btn-secondary" onClick={suggestProtocol}>
            🧠 AI Suggest
          </button>
          <button className="btn-accent" onClick={generateQR}>
            📱 Get QR
          </button>
        </div>

        {status.msg && (
          <div className={`status ${status.type}`}>{status.msg}</div>
        )}
      </div>

      <div
        style={{
          display: "grid",
          gap: "20px",
          gridTemplateColumns:
            protocols.length > 0 && qrUrl ? "1fr 1fr" : "1fr",
        }}
      >
        {protocols.length > 0 && (
          <div className="card">
            <h2>🧠 Suggested Protocols</h2>
            <div className="protocol-list">
              {protocols.map((p, i) => (
                <div key={i} className="protocol">
                  <h3>{p.title}</h3>
                  <p>{p.steps}</p>
                  <span className="tag">
                    Match: {Math.round(p.similarity * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {qrUrl && (
          <div className="card qr-container">
            <h2>Emergency Access</h2>
            <div className="qr-frame">
              <img src={qrUrl} alt="QR Code" />
            </div>
            <p className="subtitle">Scan to view {petName}'s medical profile</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/emergency/:petName" element={<Emergency />} />
    </Routes>
  );
}
