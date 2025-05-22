import * as React from "react";

export function App() {
  const dynamicMessage = React.useState("Hello from App.jsx");
  return (
    <div className="m-4">
      <h3>{dynamicMessage}</h3>
      <h4>Start editing at erpnext_mcp_server/public/js/mcp_diagnostic/App.jsx</h4>
    </div>
  );
}