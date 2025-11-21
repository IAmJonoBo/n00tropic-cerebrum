#!/usr/bin/env node

import { Server } from "@modelcontextprotocol/sdk/server/index.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  ListResourcesRequestSchema,
  ReadResourceRequestSchema,
  CallToolRequestSchema,
  ListToolsRequestSchema,
} from "@modelcontextprotocol/sdk/types.js";
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { spawn } from "child_process";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT_DIR = path.resolve(__dirname, "../../..");

class AIWorkflowMCPServer {
  constructor() {
    this.server = new Server(
      {
        name: "ai-workflow-mcp",
        version: "1.0.0",
      },
      {
        capabilities: {
          resources: {},
          tools: {},
        },
      },
    );

    this.setupHandlers();
  }

  setupHandlers() {
    // List available resources (workflow artifacts, capabilities, etc.)
    this.server.setRequestHandler(ListResourcesRequestSchema, async () => {
      const resources = [];

      // Add workflow phase resources
      const phases = [
        "planning-specs",
        "architecture-diagrams",
        "code-stubs",
        "debugging-testing",
        "review-deployment",
      ];
      phases.forEach((phase) => {
        const phaseDir = path.join(
          ROOT_DIR,
          ".dev/automation/artifacts/ai-workflows",
          phase,
        );
        if (fs.existsSync(phaseDir)) {
          const files = fs.readdirSync(phaseDir);
          files.forEach((file) => {
            resources.push({
              uri: `ai-workflow://artifact/${phase}/${file}`,
              name: `${phase}: ${file}`,
              description: `AI workflow artifact from ${phase} phase`,
              mimeType: this.getMimeType(file),
            });
          });
        }
      });

      // Add capability manifest
      const manifestPath = path.join(
        ROOT_DIR,
        "n00t/capabilities/manifest.json",
      );
      if (fs.existsSync(manifestPath)) {
        resources.push({
          uri: "ai-workflow://capabilities/manifest",
          name: "AI Workflow Capabilities",
          description: "Manifest of available AI workflow capabilities",
          mimeType: "application/json",
        });
      }

      return { resources };
    });

    // Read resource content
    this.server.setRequestHandler(
      ReadResourceRequestSchema,
      async (request) => {
        const { uri } = request.params;

        if (uri.startsWith("ai-workflow://artifact/")) {
          const artifactPath = uri.replace("ai-workflow://artifact/", "");
          const fullPath = path.join(
            ROOT_DIR,
            ".dev/automation/artifacts/ai-workflows",
            artifactPath,
          );

          if (!fs.existsSync(fullPath)) {
            throw new Error(`Artifact not found: ${fullPath}`);
          }

          const content = fs.readFileSync(fullPath, "utf8");
          return {
            contents: [
              {
                uri,
                mimeType: this.getMimeType(fullPath),
                text: content,
              },
            ],
          };
        }

        if (uri === "ai-workflow://capabilities/manifest") {
          const manifestPath = path.join(
            ROOT_DIR,
            "n00t/capabilities/manifest.json",
          );
          const content = fs.readFileSync(manifestPath, "utf8");
          return {
            contents: [
              {
                uri,
                mimeType: "application/json",
                text: content,
              },
            ],
          };
        }

        throw new Error(`Unsupported URI: ${uri}`);
      },
    );

    // List available tools (workflow execution)
    this.server.setRequestHandler(ListToolsRequestSchema, async () => {
      return {
        tools: [
          {
            name: "run_workflow_phase",
            description: "Execute a specific AI workflow phase",
            inputSchema: {
              type: "object",
              properties: {
                phase: {
                  type: "string",
                  enum: [
                    "planning",
                    "architecture",
                    "coding",
                    "debugging",
                    "review",
                  ],
                  description: "The workflow phase to execute",
                },
                interactive: {
                  type: "boolean",
                  default: true,
                  description: "Whether to run interactively or with defaults",
                },
              },
              required: ["phase"],
            },
          },
          {
            name: "run_full_workflow",
            description: "Execute the complete AI workflow sequentially",
            inputSchema: {
              type: "object",
              properties: {
                phases: {
                  type: "array",
                  items: {
                    type: "string",
                    enum: [
                      "planning",
                      "architecture",
                      "coding",
                      "debugging",
                      "review",
                    ],
                  },
                  default: [
                    "planning",
                    "architecture",
                    "coding",
                    "debugging",
                    "review",
                  ],
                  description: "Phases to execute in order",
                },
              },
            },
          },
          {
            name: "get_workflow_status",
            description:
              "Get the current status of workflow artifacts and capabilities",
            inputSchema: {
              type: "object",
              properties: {},
            },
          },
        ],
      };
    });

    // Handle tool calls
    this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
      const { name, arguments: args } = request.params;

      switch (name) {
        case "run_workflow_phase":
          return await this.runWorkflowPhase(
            args.phase,
            args.interactive !== false,
          );

        case "run_full_workflow":
          return await this.runFullWorkflow(
            args.phases || [
              "planning",
              "architecture",
              "coding",
              "debugging",
              "review",
            ],
          );

        case "get_workflow_status":
          return await this.getWorkflowStatus();

        default:
          throw new Error(`Unknown tool: ${name}`);
      }
    });
  }

  async runWorkflowPhase(phase, interactive) {
    const scriptMap = {
      planning: "planning-research.sh",
      architecture: "architecture-design.sh",
      coding: "core-coding.sh",
      debugging: "debugging-testing.sh",
      review: "review-deployment.sh",
    };

    const scriptName = scriptMap[phase];
    if (!scriptName) {
      throw new Error(`Unknown phase: ${phase}`);
    }

    const scriptPath = path.join(
      ROOT_DIR,
      ".dev/automation/scripts/ai-workflows",
      scriptName,
    );

    return new Promise((resolve, reject) => {
      const child = spawn(scriptPath, [], {
        cwd: ROOT_DIR,
        stdio: interactive ? "inherit" : ["pipe", "pipe", "pipe"],
        env: {
          ...process.env,
          FORCE_NON_INTERACTIVE: interactive ? "false" : "true",
        },
      });

      let stdout = "";
      let stderr = "";

      if (!interactive) {
        child.stdout.on("data", (data) => {
          stdout += data.toString();
        });
        child.stderr.on("data", (data) => {
          stderr += data.toString();
        });
      }

      child.on("close", (code) => {
        if (code === 0) {
          resolve({
            content: [
              {
                type: "text",
                text: `Successfully executed ${phase} phase${interactive ? "" : `:\n${stdout}`}`,
              },
            ],
          });
        } else {
          reject(
            new Error(`Phase ${phase} failed with code ${code}: ${stderr}`),
          );
        }
      });

      child.on("error", (error) => {
        reject(error);
      });
    });
  }

  async runFullWorkflow(phases) {
    const results = [];

    for (const phase of phases) {
      try {
        await this.runWorkflowPhase(phase, false);
        results.push(`${phase}: SUCCESS`);
      } catch (error) {
        results.push(`${phase}: FAILED - ${error.message}`);
      }
    }

    return {
      content: [
        {
          type: "text",
          text: `Workflow execution complete:\n${results.join("\n")}`,
        },
      ],
    };
  }

  async getWorkflowStatus() {
    const status = {
      phases: {},
      artifacts: {},
    };

    const phases = [
      "planning-specs",
      "architecture-diagrams",
      "code-stubs",
      "debugging-testing",
      "review-deployment",
    ];

    phases.forEach((phase) => {
      const phaseDir = path.join(
        ROOT_DIR,
        ".dev/automation/artifacts/ai-workflows",
        phase,
      );
      if (fs.existsSync(phaseDir)) {
        const files = fs.readdirSync(phaseDir);
        status.artifacts[phase] = files.length;
      } else {
        status.artifacts[phase] = 0;
      }
    });

    // Check script executability
    const scriptMap = {
      planning: "planning-research.sh",
      architecture: "architecture-design.sh",
      coding: "core-coding.sh",
      debugging: "debugging-testing.sh",
      review: "review-deployment.sh",
    };

    Object.entries(scriptMap).forEach(([phase, script]) => {
      const scriptPath = path.join(
        ROOT_DIR,
        ".dev/automation/scripts/ai-workflows",
        script,
      );
      status.phases[phase] = {
        script_exists: fs.existsSync(scriptPath),
        executable:
          fs.existsSync(scriptPath) &&
          (fs.statSync(scriptPath).mode & 0o111) !== 0,
      };
    });

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(status, null, 2),
        },
      ],
    };
  }

  getMimeType(filePath) {
    const ext = path.extname(filePath).toLowerCase();
    switch (ext) {
      case ".json":
        return "application/json";
      case ".md":
      case ".markdown":
        return "text/markdown";
      case ".sh":
        return "text/plain";
      case ".txt":
        return "text/plain";
      default:
        return "text/plain";
    }
  }

  async run() {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);
    console.log("AI Workflow MCP server running on stdio");
    console.log(
      "Available tools: run_workflow_phase, run_full_workflow, get_workflow_status",
    );
    console.log(
      "Available resources: workflow artifacts and capability manifests",
    );
  }
}

const server = new AIWorkflowMCPServer();
server.run().catch(console.error);
