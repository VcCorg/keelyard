import { BrowserRouter, Routes, Route } from "react-router-dom";
import { Layout } from "@/components/Layout";
import { Dashboard } from "@/pages/Dashboard";
import { Agents } from "@/pages/Agents";
import { MCPServers } from "@/pages/MCPServers";
import { ActivityFeed } from "@/pages/ActivityFeed";
import { Chat } from "@/pages/Chat";
import { Projects } from "@/pages/Projects";
import { Skills } from "@/pages/Skills";
import { Marketplace } from "@/pages/Marketplace";
import { Terminal } from "@/pages/Terminal";
import { Deployments } from "@/pages/Deployments";
import { KGContext } from "@/pages/KGContext";
import { KGDomain } from "@/pages/KGDomain";
import { KGIngest } from "@/pages/KGIngest";
import { OKFGeneration } from "@/pages/OKFGeneration";
import { DataSources } from "@/pages/DataSources";
import { CodeOnboard } from "@/pages/CodeOnboard";
import { Eval } from "@/pages/Eval";
import { CLIRunner } from "@/pages/CLIRunner";
import { Devin } from "@/pages/Devin";
import { DomainOnboarding } from "@/pages/DomainOnboarding";
import { PersonaSkills } from "@/pages/PersonaSkills";
import { Workspaces } from "@/pages/Workspaces";
import { Tasks } from "@/pages/Tasks";
import { Assignments } from "@/pages/Assignments";
import { Sessions } from "@/pages/Sessions";
import { People } from "@/pages/People";
import { SharedAgents } from "@/pages/SharedAgents";
import { SharedKG } from "@/pages/SharedKG";
import { TerminalProvider } from "@/context/TerminalContext";
import { UserProvider } from "@/context/UserContext";
import { SetupProvider } from "@/context/SetupContext";

function App() {
  return (
    <UserProvider>
    <SetupProvider>
    <TerminalProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/assignments" element={<Assignments />} />
            <Route path="/sessions" element={<Sessions />} />
            <Route path="/people" element={<People />} />
            <Route path="/shared/agents" element={<SharedAgents />} />
            <Route path="/shared/kg" element={<SharedKG />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/skills" element={<Skills />} />
            <Route path="/skills/personas" element={<PersonaSkills />} />
            <Route path="/workspaces" element={<Workspaces />} />
            <Route path="/marketplace" element={<Marketplace />} />
            <Route path="/deployments" element={<Deployments />} />
            <Route path="/mcp" element={<MCPServers />} />
            <Route path="/activity" element={<ActivityFeed />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/onboarding" element={<DomainOnboarding />} />
            <Route path="/terminal" element={<Terminal />} />
            <Route path="/kg" element={<KGContext />} />
            <Route path="/kg/ingest" element={<KGIngest />} />
            <Route path="/kg/okf" element={<OKFGeneration />} />
            <Route path="/kg/:domain" element={<KGDomain />} />
            <Route path="/data" element={<DataSources />} />
            <Route path="/code-onboard" element={<CodeOnboard />} />
            <Route path="/eval" element={<Eval />} />
            <Route path="/devin" element={<Devin />} />
            <Route path="/cli" element={<CLIRunner />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </TerminalProvider>
    </SetupProvider>
    </UserProvider>
  );
}

export default App;
