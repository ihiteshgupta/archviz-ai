#!/bin/bash
# ArchViz AI - Demo Flow Script
# Demonstrates the complete workflow: create project -> chat -> generate render

set -e

API_URL="${API_URL:-http://localhost:8000}"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${BLUE}[DEMO]${NC} $1"; }
success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║       ArchViz AI - Demo Flow              ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Check API health
log "Step 1: Checking API health..."
HEALTH=$(curl -s "$API_URL/health")
if echo "$HEALTH" | grep -q "healthy"; then
    success "API is healthy"
else
    echo "Error: API not responding at $API_URL"
    exit 1
fi

# Step 2: Check Azure AI status
log "Step 2: Checking Azure AI services..."
CHAT_STATUS=$(curl -s "$API_URL/api/chat/status")
RENDER_STATUS=$(curl -s "$API_URL/api/render/quick/status")

if echo "$CHAT_STATUS" | grep -q '"available":true'; then
    success "GPT-4o is available"
else
    echo -e "${YELLOW}Warning: GPT-4o not available. Chat features won't work.${NC}"
fi

if echo "$RENDER_STATUS" | grep -q '"available":true'; then
    success "DALL-E 3 is available"
else
    echo -e "${YELLOW}Warning: DALL-E 3 not available. Quick renders won't work.${NC}"
fi

# Step 3: Create a new project
log "Step 3: Creating a new project..."
PROJECT=$(curl -s -X POST "$API_URL/api/projects/" \
    -H "Content-Type: application/json" \
    -d '{"name": "Demo Living Room", "description": "Modern living room design demonstration"}')

PROJECT_ID=$(echo "$PROJECT" | grep -o '"id":"[^"]*"' | cut -d'"' -f4)
success "Created project: $PROJECT_ID"
echo "   Project details: $PROJECT"

# Step 4: Get design recommendations via chat
log "Step 4: Getting design recommendations from AI..."
CHAT_RESPONSE=$(curl -s -X POST "$API_URL/api/chat/" \
    -H "Content-Type: application/json" \
    -d '{
        "message": "I am designing a modern minimalist living room with large windows. What materials and color palette would you recommend?",
        "conversation_history": []
    }')

echo ""
echo -e "${GREEN}AI Recommendation:${NC}"
echo "$CHAT_RESPONSE" | grep -o '"message":"[^"]*"' | cut -d'"' -f4 | head -c 500
echo "..."
echo ""

# Step 5: Get available render styles
log "Step 5: Fetching available render styles..."
STYLES=$(curl -s "$API_URL/api/render/styles")
echo "   Available styles:"
echo "$STYLES" | grep -o '"name":"[^"]*"' | cut -d'"' -f4 | while read style; do
    echo "   - $style"
done

# Step 6: Get material library
log "Step 6: Fetching material library..."
MATERIALS=$(curl -s "$API_URL/api/materials/library")
MATERIAL_COUNT=$(echo "$MATERIALS" | grep -o '"id"' | wc -l | tr -d ' ')
success "Loaded $MATERIAL_COUNT materials"

# Step 7: Generate a quick concept render
log "Step 7: Generating quick concept render with DALL-E 3..."
echo "   (This may take 10-30 seconds...)"

RENDER_RESULT=$(curl -s -X POST "$API_URL/api/render/quick" \
    -H "Content-Type: application/json" \
    -d '{
        "room_type": "living room",
        "style": "modern minimalist",
        "materials": {
            "floor": "light oak hardwood",
            "walls": "warm white",
            "accent": "natural stone"
        },
        "additional_details": "large windows, natural light, indoor plants, minimalist furniture",
        "size": "1024x1024"
    }')

if echo "$RENDER_RESULT" | grep -q '"status":"completed"'; then
    RENDER_URL=$(echo "$RENDER_RESULT" | grep -o '"url":"[^"]*"' | head -1 | cut -d'"' -f4)
    success "Render complete!"
    echo ""
    echo -e "${GREEN}Generated Image URL:${NC}"
    echo "$RENDER_URL" | head -c 100
    echo "..."
    echo ""

    # Try to open in browser on macOS
    if [[ "$OSTYPE" == "darwin"* ]] && [[ -t 0 ]]; then
        read -p "Open render in browser? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            open "$RENDER_URL"
        fi
    fi
else
    echo -e "${YELLOW}Render may have failed. Response:${NC}"
    echo "$RENDER_RESULT" | head -c 200
fi

# Summary
echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║            Demo Complete!                 ║${NC}"
echo -e "${BLUE}╚═══════════════════════════════════════════╝${NC}"
echo ""
echo "What was demonstrated:"
echo "  1. API health check"
echo "  2. Azure AI service verification"
echo "  3. Project creation"
echo "  4. AI-powered design chat (GPT-4o)"
echo "  5. Render style listing"
echo "  6. Material library access"
echo "  7. Quick concept render (DALL-E 3)"
echo ""
echo "Next steps:"
echo "  - Open http://localhost:3000 to use the web interface"
echo "  - Upload a DWG/DXF file for floor plan analysis"
echo "  - Use the render page for more detailed visualizations"
echo ""
