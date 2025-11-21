#!/bin/bash

# AI Workflow Runner
# Orchestrates the complete AI-assisted development workflow

set -e

# Compute ROOT dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../../../.." && pwd)"
WORKFLOW_SCRIPTS_DIR="$SCRIPT_DIR"

echo "=== AI-Assisted Development Workflow Runner ==="
echo "Root Directory: $WORKSPACE_ROOT"
echo

# Available phases
declare -A PHASES=(
    ["planning"]="planning-research.sh"
    ["architecture"]="architecture-design.sh"
    ["coding"]="core-coding.sh"
    ["debugging"]="debugging-testing.sh"
    ["review"]="review-deployment.sh"
)

# Display menu
show_menu() {
    echo "Available workflow phases:"
    echo "1. Planning & Research"
    echo "2. Architecture & Design"
    echo "3. Core Coding"
    echo "4. Debugging & Testing"
    echo "5. Review & Deployment"
    echo "6. Run All Phases (Sequential)"
    echo "7. Show Workflow Status"
    echo "8. Exit"
    echo
}

# Run single phase
run_phase() {
    local phase=$1
    local script="${PHASES[$phase]}"

    if [[ -z "$script" ]]; then
        echo "Error: Unknown phase '$phase'"
        return 1
    fi

    local script_path="$WORKFLOW_SCRIPTS_DIR/$script"
    if [[ ! -f "$script_path" ]]; then
        echo "Error: Script not found: $script_path"
        return 1
    fi

    echo "Running phase: $phase"
    echo "Script: $script"
    echo

    # Run the script
    bash "$script_path"

    echo
    echo "Phase '$phase' completed successfully!"
    echo
}

# Run all phases sequentially
run_all_phases() {
    echo "Running all workflow phases sequentially..."
    echo "This will execute: Planning → Architecture → Coding → Debugging → Review"
    echo

    for phase in planning architecture coding debugging review; do
        run_phase "$phase"
        echo "Press Enter to continue to next phase..."
        read
    done

    echo "All workflow phases completed!"
}

# Show workflow status
show_status() {
    echo "=== Workflow Status ==="
    echo

    for phase in "${!PHASES[@]}"; do
        script="${PHASES[$phase]}"
        script_path="$WORKFLOW_SCRIPTS_DIR/$script"

        if [[ -f "$script_path" ]] && [[ -x "$script_path" ]]; then
            echo "✓ $phase: Ready ($script)"
        else
            echo "✗ $phase: Not ready ($script)"
        fi
    done

    echo
    echo "Artifacts directories:"
    
    # Map phase names to actual artifact directory names and locations
    for phase in "${!PHASES[@]}"; do
        # Check both possible locations
    automation_artifacts="$WORKSPACE_ROOT/.dev/automation/artifacts/ai-workflows"
        root_artifacts="$WORKSPACE_ROOT/artifacts/ai-workflows"
        
        case $phase in
            "planning")
                artifacts_path="$automation_artifacts/planning-specs"
                ;;
            "architecture")
                artifacts_path="$automation_artifacts/architecture-diagrams"
                ;;
            "coding")
                artifacts_path="$automation_artifacts/code-stubs"
                ;;
            "debugging")
                artifacts_path="$root_artifacts/debugging-testing"
                ;;
            "review")
                artifacts_path="$root_artifacts/review-deployment"
                ;;
        esac
        
        if [[ -d "$artifacts_path" ]]; then
            file_count=$(find "$artifacts_path" -type f 2>/dev/null | wc -l)
            echo "  $phase: $file_count files"
        else
            echo "  $phase: No artifacts yet"
        fi
    done
    echo
}

# Main menu loop
while true; do
    show_menu
    read -p "Select an option (1-8): " choice

    case $choice in
        1) run_phase "planning" ;;
        2) run_phase "architecture" ;;
        3) run_phase "coding" ;;
        4) run_phase "debugging" ;;
        5) run_phase "review" ;;
        6) run_all_phases ;;
        7) show_status ;;
        8) echo "Exiting workflow runner."; exit 0 ;;
        *) echo "Invalid option. Please try again." ;;
    esac

    echo
    echo "Press Enter to continue..."
    read
done