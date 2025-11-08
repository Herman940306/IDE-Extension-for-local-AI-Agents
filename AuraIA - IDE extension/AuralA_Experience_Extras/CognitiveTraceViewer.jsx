
import React from "react";

/**
 * CognitiveTraceViewer.jsx
 * Lightweight visualizer for cognitive trace JSON. Expect a list of events.
 * Props: events = [{id,timestamp,stage,model,input_snippet,output_snippet,confidence,meta,parents,notes}]
 */

export default function CognitiveTraceViewer({ events = [] }) {
  // simple node list grouped by stage
  const stages = ["system1","task_router","code_engine","system2","safety","composer"];
  const grouped = stages.map(s => ({ stage: s, items: events.filter(e => e.stage === s) }));
  return (
    <div className="p-4 bg-slate-900 text-white rounded-lg">
      <h3 className="text-lg mb-3">Cognitive Trace</h3>
      <div className="space-y-4">
        {grouped.map(g => (
          <div key={g.stage}>
            <div className="font-semibold">{g.stage.toUpperCase()}</div>
            <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-3">
              {g.items.map(it => (
                <div key={it.id} className="p-3 bg-slate-800 rounded-md border border-slate-700">
                  <div className="text-xs text-slate-400">{it.timestamp} • {it.model} • conf {Math.round(it.confidence*100)}%</div>
                  <div className="mt-2 text-sm"><strong>In:</strong> {it.input_snippet}</div>
                  <div className="mt-1 text-sm"><strong>Out:</strong> {it.output_snippet}</div>
                  <div className="mt-2 text-xs text-slate-300">{it.notes}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
