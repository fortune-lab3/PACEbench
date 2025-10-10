#!/usr/bin/env python3
"""
PACEbench - Penetration Testing Agent Benchmarking Framework
"""

import argparse
import sys
from pathlib import Path
import json

# Add project root to sys.path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from data.dataset_manager import dataset_manager
from utils.docker_manager import docker_manager
from utils.port_manager import port_manager
from utils.workflow_manager import workflow_manager, TestMode

# rich table beautify
try:
    from rich.console import Console
    from rich.table import Table
    from rich.theme import Theme
    from rich.text import Text
except ImportError:
    print("[!] rich is not installed. Please run: pip install rich")
    sys.exit(1)

# Load supported models from config/models.json
MODELS_CONFIG_PATH = "config/models.json"
def load_supported_models():
    try:
        with open(MODELS_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("models", [])
    except Exception as e:
        print(f"[red]❌ Failed to load models config: {e}")
        return []
SUPPORTED_MODELS = load_supported_models()

console = Console(theme=Theme({
    "cve": "bold cyan",
    "multiple_host": "bold magenta", 
    "full_chain": "bold yellow",
    "defense": "bold green",
    "header": "bold white on blue"
}))

def fit(text, width):
    """Fit text to width with ellipsis"""
    text = str(text)
    return text if len(text) <= width else text[:width-1] + "…"

def show_datasets():
    """Show all datasets"""
    table = Table(show_lines=True, header_style="header")
    table.add_column("ID", width=4, justify="center")
    table.add_column("Category", width=12, justify="center")
    table.add_column("Name", width=20, justify="center")
    table.add_column("Type", width=12, justify="center")
    table.add_column("Description", width=38, justify="left")

    color_map = {
        "cve": "cve",
        "multiple_host": "multiple_host",
        "full_chain": "full_chain",
        "defense": "defense"
    }

    for category in dataset_manager.list_categories():
        tasks = dataset_manager.get_datasets(category)
        for task_name, task_info in tasks.items():
            cat_disp = Text(category.upper(), style=color_map.get(category, ""))
            table.add_row(
                fit(task_info['id'], 4),
                cat_disp,
                fit(task_info['name'], 20),
                fit(task_info['type'], 12),
                fit(task_info['description'], 38)
            )
    console.print(table)

def show_task_detail(task_id):
    """Show task details"""
    task_info = dataset_manager.get_task(task_id)
    if not task_info:
        console.print(f"[red]❌ Task not found by id or name: '{task_id}'")
        return

    console.rule(f"[bold green]Task Detail: {task_info['name']}")
    console.print(f"[bold]ID:[/] {task_info['id']}")
    console.print(f"[bold]Category:[/] {task_info['category']}")
    console.print(f"[bold]Name:[/] {task_info['name']}")
    console.print(f"[bold]Type:[/] {task_info['type']}")
    console.print(f"[bold]Difficulty:[/] {task_info.get('difficulty', '')}")
    console.print(f"[bold]Description:[/]")
    console.print(task_info['description'])
    console.print(f"[bold]Solution:[/]")
    console.print(task_info['solution'])
    
    # Show environment info
    env_name = docker_manager.task_to_env.get(task_info['id'])
    if env_name:
        console.print(f"[bold]Environment:[/] {env_name}")
        allocated_ports = port_manager.get_environment_ports(env_name)
        if allocated_ports:
            console.print(f"[bold]Allocated ports:[/] {allocated_ports}")

def setup_environment(dataset=None, task=None):
    """Start specified docker environment"""
    console.print("[bold blue]🚀 Environment start mode[/]")
    
    if task:
        console.print(f"🎯 Start task environment: {task}")
        docker_manager.start_by_task(task)
    elif dataset:
        console.print(f"📁 Start category environments: {dataset}")
        docker_manager.start_by_category(dataset)
    else:
        console.print("[yellow]⚠️ You must specify a task or category[/]")
        console.print("Examples:")
        console.print("  python3 main.py env --task NAIVE-WAF")
        console.print("  python3 main.py env --dataset defense")

def run_benchmark(dataset=None, task=None, agent=None, model=None):
    """Run benchmark"""
    console.print("[bold blue]🎯 Benchmark mode[/]")
    # Pass model explicitly
    workflow_manager.set_agent_config({
        "url": "http://localhost:8000",
        "model": model if model else None
    })
    try:
        if task:
            console.print(f"🎯 Single test: {task}")
            report = workflow_manager.run_test_workflow(TestMode.SINGLE, task)
        elif dataset:
            console.print(f"📁 Category test: {dataset}")
            report = workflow_manager.run_test_workflow(TestMode.CATEGORY, dataset)
        else:
            console.print("🌍 All tests")
            report = workflow_manager.run_test_workflow(TestMode.ALL)
        # Show test result
        if report.get("status") == "completed":
            summary = report.get("summary", {})
            console.print(f"\n📊 Result:")
            console.print(f"   Total: {summary.get('total', 0)}")
            console.print(f"   Success: {summary.get('success', 0)}")
            console.print(f"   Failed: {summary.get('failed', 0)}")
            console.print(f"   Skipped: {summary.get('skipped', 0)}")
        return report
    except Exception as e:
        console.print(f"[red]❌ Benchmark failed: {e}[/]")
        return {"status": "failed", "error": str(e)}

def show_port_status():
    """Show port status"""
    console.print("[bold blue]🔗 Port status[/]")
    
    allocated_ports = port_manager.list_allocated_ports()
    if allocated_ports:
        table = Table(show_lines=True, header_style="header")
        table.add_column("Environment", width=15, justify="center")
        table.add_column("Ports", width=50, justify="left")
        
        for env_name, ports in allocated_ports.items():
            port_str = ", ".join([f"{k}:{v}" for k, v in ports.items()])
            table.add_row(env_name, port_str)
        
        console.print(table)
    else:
        console.print("[yellow]No allocated ports[/]")
    
    # Check port conflicts
    conflicts = port_manager.check_port_conflicts()
    if conflicts:
        console.print(f"[red]⚠️ Port conflicts found:[/]")
        for env_name, port_type, port in conflicts:
            console.print(f"   {env_name}.{port_type}:{port}")

def cleanup_environment(dataset=None, task=None, keep_images=False, keep_volumes=False):
    """Cleanup docker environments"""
    console.print("[bold blue]🧹 Cleanup mode[/]")
    
    remove_images = not keep_images
    remove_volumes = not keep_volumes
    
    if task:
        console.print(f"🎯 Cleanup task environment: {task}")
        result = docker_manager.cleanup_by_task(task, remove_images, remove_volumes)
    elif dataset:
        console.print(f"📁 Cleanup category environments: {dataset}")
        result = docker_manager.cleanup_by_category(dataset, remove_images, remove_volumes)
    else:
        console.print("[yellow]⚠️ You must specify a task or category for cleanup[/]")
        console.print("Examples:")
        console.print("  python3 main.py cleanup --task MIP_1")
        console.print("  python3 main.py cleanup --dataset defense")
        console.print("  python3 main.py cleanup --task MIP_1 --keep-images  # keep images")
        console.print("  python3 main.py cleanup --task MIP_1 --keep-volumes # keep volumes")
        return False
    
    if result:
        if keep_images and keep_volumes:
            console.print("[green]🎉 Cleanup done, kept images and volumes[/]")
        elif keep_images:
            console.print("[green]🎉 Cleanup done, kept images[/]")
        elif keep_volumes:
            console.print("[green]🎉 Cleanup done, kept volumes[/]")
        else:
            console.print("[green]🎉 Full cleanup done![/]")
    else:
        console.print("[red]❌ Cleanup failed[/]")
    
    return result

def show_flags(task=None):
    """Show flags for a task"""
    console.print("[bold blue]🏁 Flags[/]")
    
    if task:
        flags = docker_manager.get_task_flags(task)
        if flags:
            console.print(f"📝 Flags for task {task}:")
            table = Table(show_lines=True, header_style="header")
            table.add_column("Flag Name", width=15, justify="center")
            table.add_column("Flag Value", width=50, justify="left")
            
            for flag_name, flag_content in flags.items():
                table.add_row(flag_name, flag_content)
            
            console.print(table)
        else:
            console.print(f"[yellow]⚠️ Task {task} has no generated flags[/]")
    else:
        console.print("[yellow]⚠️ You must specify a task for flags view[/]")
        console.print("Example:")
        console.print("  python3 main.py flags --task MIP_1")

def cleanup_flag_directories():
    """Cleanup incorrectly created flag.txt directories"""
    console.print("[header]🧹 Cleanup incorrect flag.txt directories[/header]\n")
    
    try:
        success = docker_manager.cleanup_incorrect_flag_directories()
        if success:
            console.print("✅ flag directories cleanup completed")
        else:
            console.print("❌ flag directories cleanup failed")
    except Exception as e:
        console.print(f"❌ Error during cleanup: {e}")

def main():
    parser = argparse.ArgumentParser(
        description="PACEbench - Penetration Testing Agent Benchmarking Framework",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 main.py show                    # List all datasets
  python3 main.py show --task NAIVE-WAF   # Show a specific task
  python3 main.py env --task NAIVE-WAF    # Start a task env
  python3 main.py env --dataset defense   # Start a category envs
  python3 main.py benchmark --task NAIVE-WAF  # Run single benchmark
  python3 main.py benchmark --dataset defense  # Run category benchmark
  python3 main.py benchmark               # Run all benchmarks
  python3 main.py cleanup --task MIP_1    # Cleanup a task env
  python3 main.py cleanup --dataset defense  # Cleanup a category envs
  python3 main.py cleanup --task MIP_1 --keep-images  # Keep images
  python3 main.py flags --task MIP_1      # Show flags for a task
  python3 main.py cleanup-flags           # Cleanup incorrect flag.txt dirs
  python3 main.py ports                   # Show port status
  python3 main.py show --model            # Show supported models
  python3 main.py benchmark --dataset cve --model 2  # Use the 2nd model

Categories:
  cve            - CVE exploitation
  multiple_host  - Multi-host environments
  full_chain     - Full-chain attacks
  defense        - WAF bypass scenarios
        """
    )
    
    parser.add_argument(
        "mode", 
        choices=["benchmark", "env", "show", "ports", "cleanup", "flags", "cleanup-flags"], 
        help="mode"
    )
    
    parser.add_argument(
        "--dataset", 
        type=str, 
        choices=["cve", "multiple_host", "full_chain", "defense"],
        help="dataset type"
    )
    
    parser.add_argument(
        "--task", 
        type=str, 
        help="task id or name"
    )
    
    parser.add_argument(
        "--agent", 
        type=str, 
        default="default", 
        help="agent (benchmark mode only)"
    )
    
    parser.add_argument(
        "--model", 
        nargs="?",
        type=str,
        const="show",
        help="model (benchmark mode only). Support: --model, --model show, index, name"
    )
    
    parser.add_argument(
        "--keep-images", 
        action="store_true", 
        help="keep docker images (cleanup mode only)"
    )
    
    parser.add_argument(
        "--keep-volumes", 
        action="store_true", 
        help="keep docker volumes (cleanup mode only)"
    )
    
    args = parser.parse_args()

    # Model selection shortcut
    model = args.model
    if model == "show":
        console = Console()
        table = Table(title="Supported models", show_lines=True)
        table.add_column("Index", justify="center")
        table.add_column("Model", justify="left")
        for idx, m in enumerate(SUPPORTED_MODELS, 1):
            table.add_row(str(idx), m)
        console.print(table)
        return
    elif model and model.isdigit():
        idx = int(model)
        if 1 <= idx <= len(SUPPORTED_MODELS):
            model = SUPPORTED_MODELS[idx-1]
        else:
            print(f"[red]❌ Model index out of range (1-{len(SUPPORTED_MODELS)})")
            return
    # Other modes
    if args.mode == "show":
        if args.task:
            show_task_detail(args.task)
        else:
            show_datasets()
    elif args.mode == "env":
        setup_environment(args.dataset, args.task)
    elif args.mode == "benchmark":
        run_benchmark(args.dataset, args.task, args.agent, model)
    elif args.mode == "cleanup":
        keep_images = getattr(args, 'keep_images', False)
        keep_volumes = getattr(args, 'keep_volumes', False)
        cleanup_environment(args.dataset, args.task, keep_images, keep_volumes)
    elif args.mode == "flags":
        show_flags(args.task)
    elif args.mode == "cleanup-flags":
        cleanup_flag_directories()
    elif args.mode == "ports":
        show_port_status()

if __name__ == "__main__":
    main() 