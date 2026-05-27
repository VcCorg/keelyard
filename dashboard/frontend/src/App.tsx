import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Dashboard } from "@/pages/Dashboard";
import { Agents } from "@/pages/Agents";
import { MCPServers } from "@/pages/MCPServers";
import { ActivityFeed } from "@/pages/ActivityFeed";
import { Chat } from "@/pages/Chat";
import { Projects } from "@/pages/Projects";
import { Skills } from "@/pages/Skills";
import { Terminal } from "@/pages/Terminal";
import { Deployments } from "@/pages/Deployments";
import { KGContext } from "@/pages/KGContext";
import { KGDomain } from "@/pages/KGDomain";
import { TerminalProvider } from "@/context/TerminalContext";

function App() {
  return (
    <TerminalProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/skills" element={<Skills />} />
            <Route path="/deployments" element={<Deployments />} />
            <Route path="/mcp" element={<MCPServers />} />
            <Route path="/activity" element={<ActivityFeed />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/terminal" element={<Terminal />} />
            <Route path="/kg" element={<KGContext />} />
            <Route path="/kg/:domain" element={<KGDomain />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </TerminalProvider>
  );
}

export default App;
