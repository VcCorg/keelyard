import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { 
  Search, 
  Download, 
  Eye, 
  Settings, 
  Package, 
  Tag, 
  Server,
  CheckCircle,
  AlertCircle,
  Loader2
} from "lucide-react";

interface Skill {
  name: string;
  description: string;
  tags: string[];
  mcp?: any;
  auto_detect?: any;
}

interface RegistryInfo {
  configured_path: string;
  actual_path: string | null;
  exists: boolean;
  is_git_repo: boolean;
  git_remote: string | null;
  skills_count: number;
  last_updated: string | null;
}

interface ProjectSkills {
  project_path: string;
  project_name: string;
  installed_skills: Skill[];
  suggested_skills: Skill[];
  total_installed: number;
  total_suggested: number;
}

export function Skills() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [filteredSkills, setFilteredSkills] = useState<Skill[]>([]);
  const [registryInfo, setRegistryInfo] = useState<RegistryInfo | null>(null);
  const [projectSkills, setProjectSkills] = useState<ProjectSkills | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [skillContent, setSkillContent] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedTag, setSelectedTag] = useState<string>("");
  const [installing, setInstalling] = useState<string | null>(null);
  const [alert, setAlert] = useState<{ type: "success" | "error"; message: string } | null>(null);
  const [configuringRegistry, setConfiguringRegistry] = useState(false);
  const [updatingRegistry, setUpdatingRegistry] = useState(false);
  const [showRegistryConfig, setShowRegistryConfig] = useState(false);
  const [bitbucketUrl, setBitbucketUrl] = useState("");
  const [registryBranch, setRegistryBranch] = useState("develop");

  // Load skills and registry info
  useEffect(() => {
    loadSkills();
    loadRegistryInfo();
    loadProjectSkills();
  }, []);

  // Filter skills based on search and tag
  useEffect(() => {
    let filtered = skills;
    
    if (searchTerm) {
      filtered = filtered.filter(skill => 
        skill.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        skill.description.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }
    
    if (selectedTag) {
      filtered = filtered.filter(skill => 
        skill.tags.includes(selectedTag)
      );
    }
    
    setFilteredSkills(filtered);
  }, [skills, searchTerm, selectedTag]);

  const loadSkills = async () => {
    try {
      const response = await fetch("/api/skills/list");
      const data = await response.json();
      setSkills(data.skills);
    } catch (error) {
      console.error("Failed to load skills:", error);
      setAlert({ type: "error", message: "Failed to load skills from registry" });
    }
  };

  const loadRegistryInfo = async () => {
    try {
      const response = await fetch("/api/skills/registry/info");
      const data = await response.json();
      setRegistryInfo(data);
    } catch (error) {
      console.error("Failed to load registry info:", error);
    } finally {
      setLoading(false);
    }
  };

  const loadProjectSkills = async () => {
    try {
      // Try to get skills from current working directory
      const response = await fetch("/api/skills/project/.");
      if (response.ok) {
        const data = await response.json();
        setProjectSkills(data);
      }
    } catch (error) {
      console.error("Failed to load project skills:", error);
    }
  };

  const showSkillDetails = async (skillName: string) => {
    try {
      const response = await fetch(`/api/skills/show/${skillName}`);
      const data = await response.json();
      setSelectedSkill(data);
      setSkillContent(data.content || "");
    } catch (error) {
      console.error("Failed to load skill details:", error);
      setAlert({ type: "error", message: "Failed to load skill details" });
    }
  };

  const installSkill = async (skillName: string) => {
    setInstalling(skillName);
    try {
      const response = await fetch("/api/skills/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          skill_name: skillName,
          project_path: "."
        })
      });
      
      const data = await response.json();
      if (response.ok) {
        setAlert({ type: "success", message: data.message });
        loadProjectSkills(); // Refresh project skills
      } else {
        setAlert({ type: "error", message: data.detail || "Failed to install skill" });
      }
    } catch (error) {
      console.error("Failed to install skill:", error);
      setAlert({ type: "error", message: "Failed to install skill" });
    } finally {
      setInstalling(null);
    }
  };

  const configureRegistry = async () => {
    if (!bitbucketUrl.trim()) {
      setAlert({ type: "error", message: "Please enter a Bitbucket repository URL" });
      return;
    }

    setConfiguringRegistry(true);
    try {
      const response = await fetch("/api/skills/registry/configure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          bitbucket_url: bitbucketUrl.trim(),
          branch: registryBranch
        })
      });
      
      const data = await response.json();
      if (response.ok) {
        setAlert({ type: "success", message: data.message });
        setShowRegistryConfig(false);
        setBitbucketUrl("");
        loadRegistryInfo(); // Refresh registry info
        loadSkills(); // Reload skills from new registry
      } else {
        setAlert({ type: "error", message: data.detail || "Failed to configure registry" });
      }
    } catch (error) {
      console.error("Failed to configure registry:", error);
      setAlert({ type: "error", message: "Failed to configure registry" });
    } finally {
      setConfiguringRegistry(false);
    }
  };

  const updateRegistry = async () => {
    setUpdatingRegistry(true);
    try {
      const response = await fetch("/api/skills/registry/update", {
        method: "POST"
      });
      
      const data = await response.json();
      if (response.ok) {
        setAlert({ type: "success", message: data.message });
        loadRegistryInfo(); // Refresh registry info
        loadSkills(); // Reload skills from updated registry
      } else {
        setAlert({ type: "error", message: data.detail || "Failed to update registry" });
      }
    } catch (error) {
      console.error("Failed to update registry:", error);
      setAlert({ type: "error", message: "Failed to update registry" });
    } finally {
      setUpdatingRegistry(false);
    }
  };

  const getAllTags = () => {
    const tags = new Set<string>();
    skills.forEach(skill => skill.tags.forEach(tag => tags.add(tag)));
    return Array.from(tags).sort();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin" />
        <span className="ml-2">Loading skills...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Skills Management</h1>
          <p className="text-muted-foreground">
            Manage and install Agent Skills for AI code assistance
          </p>
        </div>
        <div className="flex items-center gap-2">
          {registryInfo && (
            <Badge variant={registryInfo.exists ? "default" : "destructive"}>
              {registryInfo.exists ? "Registry Connected" : "Registry Not Found"}
            </Badge>
          )}
        </div>
      </div>

      {/* Alert */}
      {alert && (
        <Alert variant={alert.type === "error" ? "destructive" : "default"}>
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{alert.message}</AlertDescription>
        </Alert>
      )}

      {/* Registry Info */}
      {registryInfo && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Settings className="h-5 w-5" />
                Skills Registry
              </div>
              <div className="flex gap-2">
                {registryInfo.is_git_repo && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={updateRegistry}
                    disabled={updatingRegistry}
                  >
                    {updatingRegistry ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      "Update"
                    )}
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowRegistryConfig(true)}
                >
                  Configure
                </Button>
              </div>
            </CardTitle>
            <CardDescription>
              Registry configuration and status
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div>
                <p className="text-sm font-medium">Status</p>
                <p className="text-sm text-muted-foreground">
                  {registryInfo.exists ? "Available" : "Not Available"}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium">Total Skills</p>
                <p className="text-sm text-muted-foreground">{registryInfo.skills_count}</p>
              </div>
              <div>
                <p className="text-sm font-medium">Git Repository</p>
                <p className="text-sm text-muted-foreground">
                  {registryInfo.is_git_repo ? "Yes" : "No"}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium">Remote</p>
                <p className="text-sm text-muted-foreground truncate">
                  {registryInfo.git_remote ? (
                    <a 
                      href={registryInfo.git_remote} 
                      target="_blank" 
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline"
                    >
                      {registryInfo.git_remote.replace("https://bitbucket.example.com/scm/", "bb:")}
                    </a>
                  ) : "N/A"}
                </p>
              </div>
              <div>
                <p className="text-sm font-medium">Path</p>
                <p className="text-sm text-muted-foreground truncate">
                  {registryInfo.actual_path?.includes("/.dva/") 
                    ? "~/.dva/" + registryInfo.actual_path.split("/.dva/")[1] 
                    : registryInfo.actual_path || "N/A"}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Registry Configuration Modal */}
      {showRegistryConfig && (
        <Card className="mt-4">
          <CardHeader>
            <CardTitle>Configure Skills Registry</CardTitle>
            <CardDescription>
              Connect to a Bitbucket repository containing skills
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Bitbucket Repository URL</label>
              <Input
                placeholder="https://bitbucket.example.com/scm/PROJECT/repo.git"
                value={bitbucketUrl}
                onChange={(e) => setBitbucketUrl(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Branch</label>
              <Input
                placeholder="develop"
                value={registryBranch}
                onChange={(e) => setRegistryBranch(e.target.value)}
                className="mt-1"
              />
            </div>
            <div className="flex gap-2">
              <Button
                onClick={configureRegistry}
                disabled={configuringRegistry || !bitbucketUrl.trim()}
              >
                {configuringRegistry ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  "Configure Registry"
                )}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setShowRegistryConfig(false);
                  setBitbucketUrl("");
                  setRegistryBranch("develop");
                }}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Main Content */}
      <Tabs defaultValue="available" className="space-y-4">
        <TabsList>
          <TabsTrigger value="available">Available Skills</TabsTrigger>
          <TabsTrigger value="installed">Installed Skills</TabsTrigger>
          <TabsTrigger value="suggested">Suggested Skills</TabsTrigger>
        </TabsList>

        {/* Available Skills Tab */}
        <TabsContent value="available" className="space-y-4">
          {/* Search and Filters */}
          <div className="flex flex-col md:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search skills..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <select
              value={selectedTag}
              onChange={(e) => setSelectedTag(e.target.value)}
              className="px-3 py-2 border rounded-md bg-background"
            >
              <option value="">All Tags</option>
              {getAllTags().map(tag => (
                <option key={tag} value={tag}>{tag}</option>
              ))}
            </select>
          </div>

          {/* Skills Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSkills.map((skill) => (
              <Card key={skill.name} className="h-fit">
                <CardHeader>
                  <CardTitle className="text-lg">{skill.name}</CardTitle>
                  <CardDescription className="line-clamp-2">
                    {skill.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Tags */}
                  <div className="flex flex-wrap gap-1">
                    {skill.tags.map((tag) => (
                      <Badge key={tag} variant="secondary" className="text-xs">
                        {tag}
                      </Badge>
                    ))}
                  </div>

                  {/* MCP Indicator */}
                  {skill.mcp && (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Server className="h-4 w-4" />
                      <span>MCP: {skill.mcp.server}</span>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => showSkillDetails(skill.name)}
                      className="flex-1"
                    >
                      <Eye className="h-4 w-4 mr-1" />
                      View
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => installSkill(skill.name)}
                      disabled={installing === skill.name}
                      className="flex-1"
                    >
                      {installing === skill.name ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4 mr-1" />
                      )}
                      Install
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* Installed Skills Tab */}
        <TabsContent value="installed" className="space-y-4">
          {projectSkills ? (
            <div>
              <div className="mb-4">
                <h3 className="text-lg font-semibold">
                  {projectSkills.project_name}
                </h3>
                <p className="text-sm text-muted-foreground">
                  {projectSkills.project_path}
                </p>
              </div>
              
              {projectSkills.installed_skills.length > 0 ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {projectSkills.installed_skills.map((skill) => (
                    <Card key={skill.name}>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <CheckCircle className="h-5 w-5 text-green-500" />
                          {skill.name}
                        </CardTitle>
                        <CardDescription>{skill.description}</CardDescription>
                      </CardHeader>
                    </Card>
                  ))}
                </div>
              ) : (
                <Card>
                  <CardContent className="text-center py-8">
                    <Package className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                    <p className="text-muted-foreground">No skills installed in this project</p>
                  </CardContent>
                </Card>
              )}
            </div>
          ) : (
            <Card>
              <CardContent className="text-center py-8">
                <AlertCircle className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No project skills found</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Suggested Skills Tab */}
        <TabsContent value="suggested" className="space-y-4">
          {projectSkills && projectSkills.suggested_skills.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {projectSkills.suggested_skills.map((skill) => (
                <Card key={skill.name}>
                  <CardHeader>
                    <CardTitle className="text-lg">{skill.name}</CardTitle>
                    <CardDescription>{skill.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex flex-wrap gap-1">
                      {skill.tags.map((tag) => (
                        <Badge key={tag} variant="outline" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                    <Button
                      size="sm"
                      onClick={() => installSkill(skill.name)}
                      disabled={installing === skill.name}
                      className="w-full"
                    >
                      {installing === skill.name ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Download className="h-4 w-4 mr-1" />
                      )}
                      Install
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            <Card>
              <CardContent className="text-center py-8">
                <Tag className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <p className="text-muted-foreground">No suggested skills available</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* Skill Details Modal/Dialog */}
      {selectedSkill && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              {selectedSkill.name}
              <Button variant="outline" onClick={() => setSelectedSkill(null)}>
                Close
              </Button>
            </CardTitle>
            <CardDescription>{selectedSkill.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-96 w-full rounded-md border p-4">
              <pre className="whitespace-pre-wrap text-sm">{skillContent}</pre>
            </ScrollArea>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
