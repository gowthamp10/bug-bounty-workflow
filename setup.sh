#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}[*] Starting Bug Bounty Agent Setup${NC}"

# Check for Go installation
if ! command -v go &> /dev/null; then
    echo -e "${YELLOW}[!] Go not found. Attempting to install...${NC}"
    # This is a generic installer, might need adjustment for specific distros
    sudo apt-get update && sudo apt-get install -y golang || { echo -e "${RED}[-][ERR] Failed to install Go. Please install it manually.${NC}"; exit 1; }
fi

echo -e "${GREEN}[+] Go is installed: $(go version)${NC}"

# Install Go tools
echo -e "${GREEN}[*] Installing Go-based tools...${NC}"

export GOPATH=$HOME/go
export PATH=$PATH:$GOPATH/bin

install_go_tool() {
    local tool=$1
    local path=$2
    echo -e "${GREEN}[*] Installing $tool...${NC}"
    go install -v $path@latest
}

install_go_tool "subfinder" "github.com/projectdiscovery/subfinder/v2/cmd/subfinder"
install_go_tool "httpx" "github.com/projectdiscovery/httpx/cmd/httpx"
install_go_tool "waybackurls" "github.com/tomnomnom/waybackurls"
install_go_tool "gau" "github.com/lc/gau/v2/cmd/gau"

# Non-fatal amass installation
echo -e "${GREEN}[*] Installing amass...${NC}"
go install -v github.com/owasp-amass/amass/v4/...@latest || echo -e "${YELLOW}[WARN] amass install failed — --deep flag will be unavailable${NC}"

# Install Python dependencies
echo -e "${GREEN}[*] Installing Python dependencies...${NC}"
pip install -r requirements.txt --break-system-packages || pip install -r requirements.txt

# Final status table
echo -e "\n${GREEN}[*] Setup Status Table:${NC}"
printf "%-20s %-10s\n" "Tool" "Status"
printf "%-20s %-10s\n" "----" "------"

check_tool() {
    if command -v $1 &> /dev/null || [ -f $HOME/go/bin/$1 ]; then
        printf "%-20s ${GREEN}%-10s${NC}\n" "$1" "INSTALLED"
    else
        printf "%-20s ${RED}%-10s${NC}\n" "$1" "MISSING"
    fi
}

check_tool "subfinder"
check_tool "httpx"
check_tool "waybackurls"
check_tool "gau"
check_tool "amass"
check_tool "python3"

echo -e "\n${GREEN}[+] Setup complete!${NC}"
exit 0
