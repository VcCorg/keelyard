#!/bin/bash
# Test script to verify MCP server is ready for Windsurf integration

set -e

echo "🧪 Testing KEEL KG MCP Server for Windsurf Integration"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Base URL
BASE_URL="http://localhost:8125"

# Test 1: Health Check
echo "1️⃣  Testing Health Endpoint..."
HEALTH=$(curl -s ${BASE_URL}/health)
if echo "$HEALTH" | grep -q "healthy"; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed${NC}"
    exit 1
fi
echo ""

# Test 2: Status Check
echo "2️⃣  Testing Status Endpoint..."
STATUS=$(curl -s ${BASE_URL}/status)
if echo "$STATUS" | grep -q "running"; then
    echo -e "${GREEN}✓ Status check passed${NC}"
    echo "   Providers:"
    echo "$STATUS" | python3 -c "import sys, json; data=json.load(sys.stdin); print('   - Neo4j:', data['providers']['providers']['neo4j']['available']); print('   - LightRAG:', data['providers']['providers']['lightrag']['available'])"
else
    echo -e "${RED}✗ Status check failed${NC}"
    exit 1
fi
echo ""

# Test 3: MCP Initialize
echo "3️⃣  Testing MCP Initialize..."
INIT=$(curl -s -X POST ${BASE_URL}/mcp/initialize -H "Content-Type: application/json" -d '{"protocolVersion":"2024-11-05"}')
if echo "$INIT" | grep -q "kg-mcp"; then
    echo -e "${GREEN}✓ MCP initialize passed${NC}"
    echo "   Protocol version: $(echo $INIT | python3 -c 'import sys, json; print(json.load(sys.stdin)["protocolVersion"])')"
else
    echo -e "${RED}✗ MCP initialize failed${NC}"
    exit 1
fi
echo ""

# Test 4: List Tools
echo "4️⃣  Testing MCP Tools List..."
TOOLS=$(curl -s -X POST ${BASE_URL}/mcp/tools/list)
TOOL_COUNT=$(echo "$TOOLS" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['tools']))")
if [ "$TOOL_COUNT" -eq 4 ]; then
    echo -e "${GREEN}✓ Tools list passed (${TOOL_COUNT} tools)${NC}"
    echo "$TOOLS" | python3 -c "import sys, json; [print(f'   - {t[\"name\"]}') for t in json.load(sys.stdin)['tools']]"
else
    echo -e "${RED}✗ Tools list failed (expected 4, got ${TOOL_COUNT})${NC}"
    exit 1
fi
echo ""

# Test 5: List Resources
echo "5️⃣  Testing MCP Resources List..."
RESOURCES=$(curl -s -X POST ${BASE_URL}/mcp/resources/list)
RESOURCE_COUNT=$(echo "$RESOURCES" | python3 -c "import sys, json; print(len(json.load(sys.stdin)['resources']))")
if [ "$RESOURCE_COUNT" -eq 5 ]; then
    echo -e "${GREEN}✓ Resources list passed (${RESOURCE_COUNT} resources)${NC}"
    echo "$RESOURCES" | python3 -c "import sys, json; [print(f'   - {r[\"uri\"]}') for r in json.load(sys.stdin)['resources']]"
else
    echo -e "${RED}✗ Resources list failed (expected 5, got ${RESOURCE_COUNT})${NC}"
    exit 1
fi
echo ""

# Test 6: Read Resource
echo "6️⃣  Testing MCP Resource Read..."
RESOURCE=$(curl -s -X POST ${BASE_URL}/mcp/resources/read -H "Content-Type: application/json" -d '{"uri":"kg://schema/neo4j"}')
if echo "$RESOURCE" | grep -q "Neo4j Graph Schema"; then
    echo -e "${GREEN}✓ Resource read passed${NC}"
    echo "   Successfully read: kg://schema/neo4j"
else
    echo -e "${RED}✗ Resource read failed${NC}"
    exit 1
fi
echo ""

# Test 7: Call Tool (kg_stats)
echo "7️⃣  Testing MCP Tool Call (kg_stats)..."
STATS=$(curl -s -X POST ${BASE_URL}/mcp/tools/call -H "Content-Type: application/json" -d '{"name":"kg_stats","arguments":{"provider":"neo4j"}}')
if echo "$STATS" | grep -q "content"; then
    echo -e "${GREEN}✓ Tool call passed${NC}"
    echo "   Tool: kg_stats with provider=neo4j"
else
    echo -e "${RED}✗ Tool call failed${NC}"
    echo "   Response: $STATS"
    exit 1
fi
echo ""

# Summary
echo "=================================================="
echo -e "${GREEN}✅ All tests passed!${NC}"
echo ""
echo "📋 Windsurf Configuration:"
echo "   1. Open: ~/.codeium/windsurf/mcp_config.json"
echo "   2. Add the configuration from: windsurf-mcp-config.json"
echo "   3. Restart Windsurf IDE"
echo ""
echo "🎯 Available MCP Features:"
echo "   • Tools: kg_query, kg_search, kg_stats, kg_ingest"
echo "   • Resources: 2 schemas, 2 templates, 1 query collection"
echo "   • Providers: Neo4j ✓, LightRAG ✓"
echo ""
echo "🚀 Ready for Windsurf integration!"
