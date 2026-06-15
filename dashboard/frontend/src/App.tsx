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
import { KGIngest } from "@/pages/KGIngest";
import { DataSources } from "@/pages/DataSources";
import { CodeOnboard } from "@/pages/CodeOnboard";
import { Eval } from "@/pages/Eval";
import { CLIRunner } from "@/pages/CLIRunner";
import { DomainOnboarding } from "@/pages/DomainOnboarding";
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
            <Route path="/onboarding" element={<DomainOnboarding />} />
            <Route path="/terminal" element={<Terminal />} />
            <Route path="/kg" element={<KGContext />} />
            <Route path="/kg/ingest" element={<KGIngest />} />
            <Route path="/kg/:domain" element={<KGDomain />} />
            <Route path="/data" element={<DataSources />} />
            <Route path="/code-onboard" element={<CodeOnboard />} />
            <Route path="/eval" element={<Eval />} />
            <Route path="/cli" element={<CLIRunner />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </TerminalProvider>
  );
}

export default App;
