import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog, simpledialog
import requests
import json
import os
import threading
import webbrowser
import glob
import subprocess
from pathlib import Path
from translations import LanguageManager
from config import ConfigManager
from PIL import Image, ImageTk
import io

# Set appearance mode and color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class MinecraftServerInstaller:
    def __init__(self):
        self.root = ctk.CTk()
        
        # Configuration management
        self.config = ConfigManager()
        
        # Load saved settings
        saved_lang = self.config.get("language", "en")
        saved_theme = self.config.get("theme", "dark")
        self.max_versions = self.config.get("max_versions", 50)
        
        print(f"Loading saved settings: lang={saved_lang}, theme={saved_theme}")  # Debug
        
        self.lang = LanguageManager(saved_lang)
        self.current_theme = saved_theme
        
        # Apply saved settings
        ctk.set_appearance_mode(self.current_theme)
        window_size = self.config.get("window_size", "900x700")
        self.root.geometry(window_size)
        self.root.resizable(True, True)
        
        # Variables
        self.server_path = tk.StringVar()
        self.server_core = tk.StringVar(value="Vanilla")
        self.server_version = tk.StringVar()
        self.eula_accepted = tk.BooleanVar()
        
        # Server data
        self.versions_data = {}
        self.available_versions = []
        self.all_versions = {}  # Store all versions for search
        
        # Server project management
        self.current_project = None
        self.project_mode = False
        
        # Set initial title
        self.root.title(self.lang.get("title"))
        
        self.create_widgets()
        self.load_version_data()
    
    def identify_server_type(self, server_dir):
        """Identify the type of Minecraft server in the given directory"""
        server_path = Path(server_dir)
        
        if not server_path.exists() or not server_path.is_dir():
            return None
        
        # Look for server jar files and characteristic folders
        files = list(server_path.glob("*.jar"))
        folders = [f.name for f in server_path.iterdir() if f.is_dir()]
        
        # Fabric server detection
        fabric_jars = [f for f in files if "fabric-server" in f.name.lower()]
        if fabric_jars or ".fabric" in folders or "mods" in folders:
            return {
                "type": "fabric",
                "jar_file": fabric_jars[0] if fabric_jars else None,
                "version": self.extract_version_from_jar(fabric_jars[0]) if fabric_jars else None,
                "supports_mods": True,
                "supports_plugins": False
            }
        
        # Paper server detection
        paper_jars = [f for f in files if "paper" in f.name.lower()]
        if paper_jars:
            return {
                "type": "paper",
                "jar_file": paper_jars[0],
                "version": self.extract_version_from_jar(paper_jars[0]),
                "supports_mods": False,
                "supports_plugins": True
            }
        
        # Spigot server detection
        spigot_jars = [f for f in files if "spigot" in f.name.lower()]
        if spigot_jars:
            return {
                "type": "spigot",
                "jar_file": spigot_jars[0],
                "version": self.extract_version_from_jar(spigot_jars[0]),
                "supports_mods": False,
                "supports_plugins": True
            }
        
        # Vanilla server detection
        vanilla_jars = [f for f in files if f.name.lower() in ["server.jar", "minecraft_server.jar"]]
        if vanilla_jars:
            return {
                "type": "vanilla",
                "jar_file": vanilla_jars[0],
                "version": None,  # Hard to extract from vanilla jars
                "supports_mods": False,
                "supports_plugins": False
            }
        
        # Check if it's a potential server directory with plugins or mods
        if "plugins" in folders:
            return {
                "type": "unknown_plugin_server",
                "jar_file": files[0] if files else None,
                "version": None,
                "supports_mods": False,
                "supports_plugins": True
            }
        elif "mods" in folders:
            return {
                "type": "unknown_mod_server", 
                "jar_file": files[0] if files else None,
                "version": None,
                "supports_mods": True,
                "supports_plugins": False
            }
        
        return None
    
    def extract_version_from_jar(self, jar_path):
        """Extract version information from jar filename"""
        if not jar_path:
            return None
        
        import re
        filename = jar_path.name
        
        # Common patterns for version extraction
        patterns = [
            r'(\d+\.\d+\.\d+)',  # x.y.z
            r'(\d+\.\d+)',       # x.y
            r'mc(\d+\.\d+\.\d+)', # mc prefix
            r'(\d+w\d+[a-z])',   # snapshot format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, filename)
            if match:
                return match.group(1)
        
        return None
    
    def open_server_project(self):
        """Open and manage an existing server project"""
        project_dir = filedialog.askdirectory(title="Select Server Project Directory")
        if not project_dir:
            return
        
        # Identify the server type
        server_info = self.identify_server_type(project_dir)
        
        if not server_info:
            messagebox.showerror(self.lang.get("error"), self.lang.get("no_server_found"))
            return
        
        # Store project information
        self.current_project = {
            "path": Path(project_dir),
            "info": server_info
        }
        
        self.project_mode = True
        
        # Show project management interface
        self.show_project_management()
    
    def show_project_management(self):
        """Display the server project management interface"""
        if not self.current_project:
            return
        
        # Create project management window
        project_window = ctk.CTkToplevel(self.root)
        project_window.title(f"{self.lang.get('server_manager')} - {self.current_project['info']['type'].title()}")
        project_window.geometry("800x600")
        project_window.resizable(True, True)
        
        # Add close event handler for server manager window
        def on_project_window_closing():
            print("Project window closing...")  # Debug
            try:
                # Check if server is running and warn user
                server_running = self.is_server_running()
                print(f"Server running check: {server_running}")  # Debug
                
                if server_running:
                    print("Showing server running dialog...")  # Debug
                    result = messagebox.askyesnocancel(
                        self.lang.get("server_running_warning"),
                        self.lang.get("server_running_close_options"),
                        icon="warning"
                    )
                    print(f"Dialog result: {result}")  # Debug
                    
                    if result is None:  # Cancel
                        print("User cancelled - not closing project window")  # Debug
                        return  # Don't close
                    elif result:  # Yes - shutdown server and close
                        print("User chose to shutdown server")  # Debug
                        self.shutdown_server_on_exit()
                    else:  # No - close GUI but leave server running
                        print("User chose to leave server running")  # Debug
                        self.leave_server_running_on_exit()
                else:
                    print("No server running, proceeding with normal close")  # Debug
                
                # Close the project window
                print("Destroying project window...")  # Debug
                project_window.destroy()
                    
            except Exception as e:
                print(f"Error during project window shutdown: {e}")
                # On error, still close
                project_window.destroy()
        
        project_window.protocol("WM_DELETE_WINDOW", on_project_window_closing)
        
        # Make window modal
        project_window.transient(self.root)
        project_window.grab_set()
        
        # Main notebook for different management sections
        notebook = ctk.CTkTabview(project_window)
        notebook.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Server Info Tab
        self.create_server_info_tab(notebook)
        
        # Server Properties Tab
        self.create_server_properties_tab(notebook)
        
        # Mods/Plugins Tab (depending on server type)
        if self.current_project['info']['supports_mods']:
            self.create_mods_tab(notebook)
        elif self.current_project['info']['supports_plugins']:
            self.create_plugins_tab(notebook)
        
        # World Management Tab
        self.create_world_management_tab(notebook)
        
        # Player Management Tab
        self.create_player_management_tab(notebook)
        
        # Server Console Tab
        self.create_server_console_tab(notebook)
        
        # Server process status file
        self.server_status_file = self.current_project["path"] / ".server_status.json"
        
        # Check for existing running server when opening project
        self.check_existing_server_status()
    
    def create_server_info_tab(self, notebook):
        """Create the server information tab"""
        info_tab = notebook.add("Server Info")
        
        info = self.current_project['info']
        
        # Server Type
        type_frame = ctk.CTkFrame(info_tab)
        type_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(type_frame, text="Server Type:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(type_frame, text=info['type'].title()).pack(anchor="w", padx=20, pady=(0, 20))
        
        # Server Jar
        if info['jar_file']:
            jar_frame = ctk.CTkFrame(info_tab)
            jar_frame.pack(fill="x", padx=10, pady=10)
            
            ctk.CTkLabel(jar_frame, text="Server Jar:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
            ctk.CTkLabel(jar_frame, text=info['jar_file'].name).pack(anchor="w", padx=20, pady=(0, 20))
        
        # Version
        if info['version']:
            version_frame = ctk.CTkFrame(info_tab)
            version_frame.pack(fill="x", padx=10, pady=10)
            
            ctk.CTkLabel(version_frame, text="Version:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
            ctk.CTkLabel(version_frame, text=info['version']).pack(anchor="w", padx=20, pady=(0, 20))
        
        # Capabilities
        caps_frame = ctk.CTkFrame(info_tab)
        caps_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(caps_frame, text="Capabilities:", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=20, pady=(20, 5))
        
        if info['supports_mods']:
            ctk.CTkLabel(caps_frame, text="✓ Supports Mods", text_color="green").pack(anchor="w", padx=20, pady=2)
        else:
            ctk.CTkLabel(caps_frame, text="✗ No Mod Support", text_color="gray").pack(anchor="w", padx=20, pady=2)
            
        if info['supports_plugins']:
            ctk.CTkLabel(caps_frame, text="✓ Supports Plugins", text_color="green").pack(anchor="w", padx=20, pady=2)
        else:
            ctk.CTkLabel(caps_frame, text="✗ No Plugin Support", text_color="gray").pack(anchor="w", padx=20, pady=(2, 20))
    
    def create_server_properties_tab(self, notebook):
        """Create the server.properties editor tab"""
        properties_tab = notebook.add(self.lang.get("server_properties"))
        
        # Load or create server.properties
        properties_file = self.current_project["path"] / "server.properties"
        self.server_properties = self.load_server_properties(properties_file)
        
        # Scrollable frame for properties
        props_frame = ctk.CTkScrollableFrame(properties_tab, width=750, height=500)
        props_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Store property widgets for saving
        self.property_widgets = {}
        
        # Basic Server Settings
        basic_frame = ctk.CTkFrame(props_frame)
        basic_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(basic_frame, text=self.lang.get("basic_settings"), 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        # Server Name (MOTD)
        self.create_property_field(basic_frame, "motd", self.lang.get("server_name"), "A Minecraft Server")
        
        # Max Players
        self.create_property_field(basic_frame, "max-players", self.lang.get("max_players"), "20", "number")
        
        # Difficulty
        difficulty_frame = ctk.CTkFrame(basic_frame)
        difficulty_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(difficulty_frame, text=self.lang.get("difficulty")).pack(side="left", padx=10, pady=10)
        
        # Map numeric values to text for difficulty
        difficulty_mapping = {"0": "peaceful", "1": "easy", "2": "normal", "3": "hard"}
        difficulty_reverse = {"peaceful": "0", "easy": "1", "normal": "2", "hard": "3"}
        
        current_difficulty = self.server_properties.get("difficulty", "1")
        # Convert numeric to text if needed
        if current_difficulty in difficulty_mapping:
            display_difficulty = difficulty_mapping[current_difficulty]
        else:
            display_difficulty = current_difficulty if current_difficulty in ["peaceful", "easy", "normal", "hard"] else "easy"
        
        difficulty_var = tk.StringVar(value=display_difficulty)
        self.property_widgets["difficulty"] = difficulty_var
        
        # Store the reverse mapping for saving
        self.difficulty_reverse_mapping = difficulty_reverse
        
        difficulty_menu = ctk.CTkOptionMenu(difficulty_frame, values=["peaceful", "easy", "normal", "hard"], variable=difficulty_var)
        difficulty_menu.pack(side="right", padx=10, pady=10)
        
        # Gamemode
        gamemode_frame = ctk.CTkFrame(basic_frame)
        gamemode_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(gamemode_frame, text=self.lang.get("gamemode")).pack(side="left", padx=10, pady=10)
        
        # Map numeric values to text for gamemode
        gamemode_mapping = {"0": "survival", "1": "creative", "2": "adventure", "3": "spectator"}
        gamemode_reverse = {"survival": "0", "creative": "1", "adventure": "2", "spectator": "3"}
        
        current_gamemode = self.server_properties.get("gamemode", "0")
        # Convert numeric to text if needed
        if current_gamemode in gamemode_mapping:
            display_gamemode = gamemode_mapping[current_gamemode]
        else:
            display_gamemode = current_gamemode if current_gamemode in ["survival", "creative", "adventure", "spectator"] else "survival"
        
        gamemode_var = tk.StringVar(value=display_gamemode)
        self.property_widgets["gamemode"] = gamemode_var
        
        # Store the reverse mapping for saving
        self.gamemode_reverse_mapping = gamemode_reverse
        
        gamemode_menu = ctk.CTkOptionMenu(gamemode_frame, values=["survival", "creative", "adventure", "spectator"], variable=gamemode_var)
        gamemode_menu.pack(side="right", padx=10, pady=10)
        
        # Online Mode
        online_var = tk.BooleanVar(value=self.server_properties.get("online-mode", "true") == "true")
        self.property_widgets["online-mode"] = online_var
        online_checkbox = ctk.CTkCheckBox(basic_frame, text=self.lang.get("online_mode"), variable=online_var)
        online_checkbox.pack(anchor="w", padx=20, pady=5)
        
        # World Settings
        world_frame = ctk.CTkFrame(props_frame)
        world_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(world_frame, text=self.lang.get("world_settings"), 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        # Level Name
        self.create_property_field(world_frame, "level-name", self.lang.get("world_name"), "world")
        
        # Level Seed
        self.create_property_field(world_frame, "level-seed", self.lang.get("world_seed"), "")
        
        # Generate Structures
        structures_var = tk.BooleanVar(value=self.server_properties.get("generate-structures", "true") == "true")
        self.property_widgets["generate-structures"] = structures_var
        structures_checkbox = ctk.CTkCheckBox(world_frame, text=self.lang.get("generate_structures"), variable=structures_var)
        structures_checkbox.pack(anchor="w", padx=20, pady=5)
        
        # Allow Nether
        nether_var = tk.BooleanVar(value=self.server_properties.get("allow-nether", "true") == "true")
        self.property_widgets["allow-nether"] = nether_var
        nether_checkbox = ctk.CTkCheckBox(world_frame, text=self.lang.get("allow_nether"), variable=nether_var)
        nether_checkbox.pack(anchor="w", padx=20, pady=5)
        
        # Advanced Settings
        advanced_frame = ctk.CTkFrame(props_frame)
        advanced_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(advanced_frame, text=self.lang.get("advanced_settings"), 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        # Server Port
        self.create_property_field(advanced_frame, "server-port", self.lang.get("server_port"), "25565", "number")
        
        # View Distance
        self.create_property_field(advanced_frame, "view-distance", self.lang.get("view_distance"), "10", "number")
        
        # PVP
        pvp_var = tk.BooleanVar(value=self.server_properties.get("pvp", "true") == "true")
        self.property_widgets["pvp"] = pvp_var
        pvp_checkbox = ctk.CTkCheckBox(advanced_frame, text=self.lang.get("enable_pvp"), variable=pvp_var)
        pvp_checkbox.pack(anchor="w", padx=20, pady=5)
        
        # Save button
        save_button = ctk.CTkButton(props_frame, text=self.lang.get("save_properties"), 
                                   command=self.save_server_properties, 
                                   font=ctk.CTkFont(size=14, weight="bold"), height=40)
        save_button.pack(pady=20)
    
    def create_property_field(self, parent, key, label, default_value, field_type="text"):
        """Create a property input field"""
        field_frame = ctk.CTkFrame(parent)
        field_frame.pack(fill="x", padx=20, pady=5)
        
        ctk.CTkLabel(field_frame, text=label).pack(side="left", padx=10, pady=10)
        
        if field_type == "number":
            var = tk.StringVar(value=self.server_properties.get(key, default_value))
            entry = ctk.CTkEntry(field_frame, textvariable=var, width=100)
        else:
            var = tk.StringVar(value=self.server_properties.get(key, default_value))
            entry = ctk.CTkEntry(field_frame, textvariable=var, width=300)
        
        entry.pack(side="right", padx=10, pady=10)
        self.property_widgets[key] = var
    
    def load_server_properties(self, properties_file):
        """Load server.properties file"""
        properties = {}
        
        if properties_file.exists():
            try:
                with open(properties_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                properties[key.strip()] = value.strip()
            except Exception as e:
                print(f"Error loading server.properties: {e}")
        
        return properties
    
    def save_server_properties(self):
        """Save server.properties file"""
        try:
            properties_file = self.current_project["path"] / "server.properties"
            
            # Store old properties for comparison
            old_properties = self.server_properties.copy()
            
            # Update properties from widgets
            for key, widget in self.property_widgets.items():
                if isinstance(widget, tk.BooleanVar):
                    self.server_properties[key] = "true" if widget.get() else "false"
                else:
                    value = widget.get()
                    # Convert text values back to numeric for certain properties
                    if key == "difficulty" and hasattr(self, 'difficulty_reverse_mapping'):
                        value = self.difficulty_reverse_mapping.get(value, value)
                    elif key == "gamemode" and hasattr(self, 'gamemode_reverse_mapping'):
                        value = self.gamemode_reverse_mapping.get(value, value)
                    
                    self.server_properties[key] = value
            
            # Write to file
            with open(properties_file, 'w', encoding='utf-8') as f:
                f.write("#Minecraft server properties\n")
                f.write("#Generated by Minecraft Server Installer\n")
                for key, value in self.server_properties.items():
                    f.write(f"{key}={value}\n")
            
            # Apply changes to running server if possible
            self.apply_properties_to_running_server(old_properties, self.server_properties)
            
            messagebox.showinfo(self.lang.get("success"), self.lang.get("properties_saved"))
            
        except Exception as e:
            messagebox.showerror(self.lang.get("error"), f"Failed to save properties: {e}")
    
    def apply_properties_to_running_server(self, old_props, new_props):
        """Apply property changes to running server where possible"""
        if not self.server_process or self.server_process.poll() is not None:
            # Server not running, show info about restart requirement
            messagebox.showinfo(self.lang.get("info"), self.lang.get("properties_will_apply_on_restart"))
            return
        
        # Properties that can be applied immediately via commands
        immediate_properties = {
            'difficulty': self.apply_difficulty_change,
            'pvp': self.apply_pvp_change,
            'max-players': self.apply_max_players_change,
            'gamemode': self.apply_gamemode_change,
            'motd': self.apply_motd_change
        }
        
        # Properties that require restart
        restart_required_properties = {
            'server-port', 'online-mode', 'level-name', 'level-seed', 
            'generate-structures', 'allow-nether', 'view-distance'
        }
        
        applied_immediately = []
        requires_restart = []
        
        # Check for changes and apply what we can
        for key, new_value in new_props.items():
            old_value = old_props.get(key, "")
            if old_value != new_value:
                if key in immediate_properties:
                    try:
                        immediate_properties[key](new_value)
                        applied_immediately.append(key)
                    except Exception as e:
                        print(f"Failed to apply {key}: {e}")
                elif key in restart_required_properties:
                    requires_restart.append(key)
        
        # Show feedback to user
        self.show_properties_feedback(applied_immediately, requires_restart)
    
    def apply_difficulty_change(self, value):
        """Apply difficulty change to running server"""
        # Convert text value to what the server command expects
        difficulty_names = {"0": "peaceful", "1": "easy", "2": "normal", "3": "hard"}
        if value in difficulty_names:
            command_value = difficulty_names[value]
        else:
            command_value = value
        
        command = f"difficulty {command_value}"
        self.send_server_command_silent(command)
        self.log_property_change("difficulty", command_value)
    
    def apply_pvp_change(self, value):
        """Apply PVP change to running server"""
        # PVP changes require restart, but we can warn players
        if value.lower() == "true":
            self.send_server_command_silent("say PVP will be enabled after server restart")
        else:
            self.send_server_command_silent("say PVP will be disabled after server restart")
        self.log_property_change("pvp", value, restart_required=True)
    
    def apply_max_players_change(self, value):
        """Apply max players change to running server"""
        # Max players requires restart, inform players
        self.send_server_command_silent(f"say Server player limit changed to {value} (restart required)")
        self.log_property_change("max-players", value, restart_required=True)
    
    def apply_gamemode_change(self, value):
        """Apply gamemode change to running server"""
        # Convert text value to what the server command expects
        gamemode_names = {"0": "survival", "1": "creative", "2": "adventure", "3": "spectator"}
        if value in gamemode_names:
            command_value = gamemode_names[value]
        else:
            command_value = value
        
        # This only affects new players, current players keep their gamemode
        self.send_server_command_silent(f"say Default gamemode changed to {command_value} for new players")
        self.log_property_change("gamemode", command_value)
    
    def apply_motd_change(self, value):
        """Apply MOTD change to running server"""
        # MOTD requires restart to show in server list
        self.send_server_command_silent("say Server description updated (will show after restart)")
        self.log_property_change("motd", value, restart_required=True)
    
    def send_server_command_silent(self, command):
        """Send command to server without showing in UI"""
        if self.server_process and self.server_process.poll() is None:
            try:
                self.server_process.stdin.write(f"{command}\n")
                self.server_process.stdin.flush()
            except Exception as e:
                print(f"Failed to send command {command}: {e}")
    
    def log_property_change(self, property_name, value, restart_required=False):
        """Log property change in console"""
        if hasattr(self, 'console_output') and self.console_output:
            restart_note = " (restart required)" if restart_required else ""
            message = f"Property '{property_name}' changed to '{value}'{restart_note}"
            self.console_output.insert("end", f"\n[{self.get_timestamp()}] {message}")
            self.console_output.see("end")
    
    def show_properties_feedback(self, applied_immediately, requires_restart):
        """Show feedback about property changes"""
        if applied_immediately or requires_restart:
            feedback_parts = []
            
            if applied_immediately:
                feedback_parts.append(self.lang.get("properties_applied_immediately", len(applied_immediately)))
            
            if requires_restart:
                feedback_parts.append(self.lang.get("properties_require_restart", len(requires_restart)))
                
                # Show restart button option
                if messagebox.askyesno(self.lang.get("restart_server_question"), 
                                     self.lang.get("restart_server_for_changes")):
                    self.restart_server()
            
            # Show detailed feedback
            feedback_message = "\n\n".join(feedback_parts)
            if applied_immediately:
                feedback_message += f"\n\n{self.lang.get('applied_immediately')}: {', '.join(applied_immediately)}"
            if requires_restart:
                feedback_message += f"\n\n{self.lang.get('requires_restart')}: {', '.join(requires_restart)}"
            
            messagebox.showinfo(self.lang.get("properties_updated"), feedback_message)
    
    def create_mods_tab(self, notebook):
        """Create the mods management tab"""
        mods_tab = notebook.add(self.lang.get("mods"))
        
        # Main scrollable container
        mods_container = ctk.CTkScrollableFrame(mods_tab, width=750, height=550)
        mods_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        header_frame = ctk.CTkFrame(mods_container)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header_frame, text=self.lang.get("installed_mods"), 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=20, pady=20)
        
        refresh_btn = ctk.CTkButton(header_frame, text=self.lang.get("refresh"), 
                                   command=self.refresh_mods, width=100)
        refresh_btn.pack(side="right", padx=20, pady=20)
        
        # Mods list
        mods_list_frame = ctk.CTkFrame(mods_container)
        mods_list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrollable frame for mods
        self.mods_scroll_frame = ctk.CTkScrollableFrame(mods_list_frame, width=750, height=400)
        self.mods_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Controls
        controls_frame = ctk.CTkFrame(mods_container)
        controls_frame.pack(fill="x", padx=10, pady=10)
        
        add_mod_btn = ctk.CTkButton(controls_frame, text=self.lang.get("add_mod"), 
                                   command=self.add_mod, width=120)
        add_mod_btn.pack(side="left", padx=10, pady=15)
        
        remove_mod_btn = ctk.CTkButton(controls_frame, text=self.lang.get("remove_selected"), 
                                      command=self.remove_selected_mod, width=120)
        remove_mod_btn.pack(side="left", padx=10, pady=15)
        
        open_mods_folder_btn = ctk.CTkButton(controls_frame, text=self.lang.get("open_mods_folder"), 
                                            command=self.open_mods_folder, width=140)
        open_mods_folder_btn.pack(side="right", padx=10, pady=15)
        
        # Load mods
        self.refresh_mods()
    
    def refresh_mods(self):
        """Refresh the mods list"""
        # Clear existing widgets
        for widget in self.mods_scroll_frame.winfo_children():
            widget.destroy()
        
        mods_path = self.current_project["path"] / "mods"
        
        if not mods_path.exists():
            mods_path.mkdir()
            ctk.CTkLabel(self.mods_scroll_frame, text=self.lang.get("no_mods_found")).pack(pady=50)
            return
        
        self.mod_checkboxes = {}
        mod_files = list(mods_path.glob("*.jar"))
        
        if not mod_files:
            ctk.CTkLabel(self.mods_scroll_frame, text=self.lang.get("no_mods_found")).pack(pady=50)
            return
        
        for mod_file in sorted(mod_files):
            mod_frame = ctk.CTkFrame(self.mods_scroll_frame)
            mod_frame.pack(fill="x", padx=10, pady=5)
            
            # Checkbox for selection
            var = tk.BooleanVar()
            self.mod_checkboxes[mod_file.name] = var
            checkbox = ctk.CTkCheckBox(mod_frame, text="", variable=var, width=30)
            checkbox.pack(side="left", padx=10, pady=10)
            
            # Mod info
            info_frame = ctk.CTkFrame(mod_frame)
            info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=5)
            
            # Mod name
            ctk.CTkLabel(info_frame, text=mod_file.name, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
            
            # File size
            size_mb = mod_file.stat().st_size / (1024 * 1024)
            ctk.CTkLabel(info_frame, text=f"{self.lang.get('file_size')}: {size_mb:.1f} MB", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10, pady=(0, 10))
    
    def add_mod(self):
        """Add a new mod file"""
        file_path = filedialog.askopenfilename(
            title=self.lang.get("select_mod_file"),
            filetypes=[("JAR files", "*.jar"), ("All files", "*.*")]
        )
        
        if file_path:
            mods_path = self.current_project["path"] / "mods"
            mods_path.mkdir(exist_ok=True)
            
            import shutil
            destination = mods_path / Path(file_path).name
            
            try:
                shutil.copy2(file_path, destination)
                messagebox.showinfo(self.lang.get("success"), self.lang.get("mod_added"))
                self.refresh_mods()
            except Exception as e:
                messagebox.showerror(self.lang.get("error"), f"Failed to add mod: {e}")
    
    def remove_selected_mod(self):
        """Remove selected mods"""
        selected_mods = [name for name, var in self.mod_checkboxes.items() if var.get()]
        
        if not selected_mods:
            messagebox.showwarning(self.lang.get("warning"), self.lang.get("no_mods_selected"))
            return
        
        if messagebox.askyesno(self.lang.get("confirm"), self.lang.get("confirm_remove_mods", len(selected_mods))):
            mods_path = self.current_project["path"] / "mods"
            
            for mod_name in selected_mods:
                mod_file = mods_path / mod_name
                try:
                    mod_file.unlink()
                except Exception as e:
                    messagebox.showerror(self.lang.get("error"), f"Failed to remove {mod_name}: {e}")
            
            self.refresh_mods()
    
    def open_mods_folder(self):
        """Open the mods folder in file explorer"""
        mods_path = self.current_project["path"] / "mods"
        mods_path.mkdir(exist_ok=True)
        
        import subprocess
        import platform
        
        try:
            if platform.system() == "Windows":
                os.startfile(mods_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", mods_path])
            else:  # Linux
                subprocess.run(["xdg-open", mods_path])
        except Exception as e:
            messagebox.showerror(self.lang.get("error"), f"Failed to open mods folder: {e}")
    
    def create_plugins_tab(self, notebook):
        """Create the plugins management tab"""
        plugins_tab = notebook.add(self.lang.get("plugins"))
        
        # Main scrollable container
        plugins_container = ctk.CTkScrollableFrame(plugins_tab, width=750, height=550)
        plugins_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        header_frame = ctk.CTkFrame(plugins_container)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header_frame, text=self.lang.get("installed_plugins"), 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=20, pady=20)
        
        refresh_btn = ctk.CTkButton(header_frame, text=self.lang.get("refresh"), 
                                   command=self.refresh_plugins, width=100)
        refresh_btn.pack(side="right", padx=20, pady=20)
        
        # Plugins list
        plugins_list_frame = ctk.CTkFrame(plugins_container)
        plugins_list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrollable frame for plugins
        self.plugins_scroll_frame = ctk.CTkScrollableFrame(plugins_list_frame, width=750, height=400)
        self.plugins_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Controls
        controls_frame = ctk.CTkFrame(plugins_container)
        controls_frame.pack(fill="x", padx=10, pady=10)
        
        add_plugin_btn = ctk.CTkButton(controls_frame, text=self.lang.get("add_plugin"), 
                                      command=self.add_plugin, width=120)
        add_plugin_btn.pack(side="left", padx=10, pady=15)
        
        remove_plugin_btn = ctk.CTkButton(controls_frame, text=self.lang.get("remove_selected"), 
                                         command=self.remove_selected_plugin, width=120)
        remove_plugin_btn.pack(side="left", padx=10, pady=15)
        
        open_plugins_folder_btn = ctk.CTkButton(controls_frame, text=self.lang.get("open_plugins_folder"), 
                                               command=self.open_plugins_folder, width=140)
        open_plugins_folder_btn.pack(side="right", padx=10, pady=15)
        
        # Load plugins
        self.refresh_plugins()
    
    def refresh_plugins(self):
        """Refresh the plugins list"""
        # Clear existing widgets
        for widget in self.plugins_scroll_frame.winfo_children():
            widget.destroy()
        
        plugins_path = self.current_project["path"] / "plugins"
        
        if not plugins_path.exists():
            plugins_path.mkdir()
            ctk.CTkLabel(self.plugins_scroll_frame, text=self.lang.get("no_plugins_found")).pack(pady=50)
            return
        
        self.plugin_checkboxes = {}
        plugin_files = list(plugins_path.glob("*.jar"))
        
        if not plugin_files:
            ctk.CTkLabel(self.plugins_scroll_frame, text=self.lang.get("no_plugins_found")).pack(pady=50)
            return
        
        for plugin_file in sorted(plugin_files):
            plugin_frame = ctk.CTkFrame(self.plugins_scroll_frame)
            plugin_frame.pack(fill="x", padx=10, pady=5)
            
            # Checkbox for selection
            var = tk.BooleanVar()
            self.plugin_checkboxes[plugin_file.name] = var
            checkbox = ctk.CTkCheckBox(plugin_frame, text="", variable=var, width=30)
            checkbox.pack(side="left", padx=10, pady=10)
            
            # Plugin info
            info_frame = ctk.CTkFrame(plugin_frame)
            info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=5)
            
            # Plugin name
            ctk.CTkLabel(info_frame, text=plugin_file.name, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
            
            # File size
            size_mb = plugin_file.stat().st_size / (1024 * 1024)
            ctk.CTkLabel(info_frame, text=f"{self.lang.get('file_size')}: {size_mb:.1f} MB", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10, pady=(0, 10))
    
    def add_plugin(self):
        """Add a new plugin file"""
        file_path = filedialog.askopenfilename(
            title=self.lang.get("select_plugin_file"),
            filetypes=[("JAR files", "*.jar"), ("All files", "*.*")]
        )
        
        if file_path:
            plugins_path = self.current_project["path"] / "plugins"
            plugins_path.mkdir(exist_ok=True)
            
            import shutil
            destination = plugins_path / Path(file_path).name
            
            try:
                shutil.copy2(file_path, destination)
                messagebox.showinfo(self.lang.get("success"), self.lang.get("plugin_added"))
                self.refresh_plugins()
            except Exception as e:
                messagebox.showerror(self.lang.get("error"), f"Failed to add plugin: {e}")
    
    def remove_selected_plugin(self):
        """Remove selected plugins"""
        selected_plugins = [name for name, var in self.plugin_checkboxes.items() if var.get()]
        
        if not selected_plugins:
            messagebox.showwarning(self.lang.get("warning"), self.lang.get("no_plugins_selected"))
            return
        
        if messagebox.askyesno(self.lang.get("confirm"), self.lang.get("confirm_remove_plugins", len(selected_plugins))):
            plugins_path = self.current_project["path"] / "plugins"
            
            for plugin_name in selected_plugins:
                plugin_file = plugins_path / plugin_name
                try:
                    plugin_file.unlink()
                except Exception as e:
                    messagebox.showerror(self.lang.get("error"), f"Failed to remove {plugin_name}: {e}")
            
            self.refresh_plugins()
    
    def open_plugins_folder(self):
        """Open the plugins folder in file explorer"""
        plugins_path = self.current_project["path"] / "plugins"
        plugins_path.mkdir(exist_ok=True)
        
        import subprocess
        import platform
        
        try:
            if platform.system() == "Windows":
                os.startfile(plugins_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", plugins_path])
            else:  # Linux
                subprocess.run(["xdg-open", plugins_path])
        except Exception as e:
            messagebox.showerror(self.lang.get("error"), f"Failed to open plugins folder: {e}")
    
    def create_world_management_tab(self, notebook):
        """Create the world management tab"""
        world_tab = notebook.add(self.lang.get("worlds"))
        
        # Main scrollable container
        worlds_container = ctk.CTkScrollableFrame(world_tab, width=750, height=550)
        worlds_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header
        header_frame = ctk.CTkFrame(worlds_container)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(header_frame, text=self.lang.get("world_management"), 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(side="left", padx=20, pady=20)
        
        refresh_btn = ctk.CTkButton(header_frame, text=self.lang.get("refresh"), 
                                   command=self.refresh_worlds, width=100)
        refresh_btn.pack(side="right", padx=20, pady=20)
        
        # Worlds list
        worlds_list_frame = ctk.CTkFrame(worlds_container)
        worlds_list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Scrollable frame for worlds
        self.worlds_scroll_frame = ctk.CTkScrollableFrame(worlds_list_frame, width=750, height=300)
        self.worlds_scroll_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Controls
        controls_frame = ctk.CTkFrame(worlds_container)
        controls_frame.pack(fill="x", padx=10, pady=10)
        
        import_world_btn = ctk.CTkButton(controls_frame, text=self.lang.get("import_world"), 
                                        command=self.import_world, width=120)
        import_world_btn.pack(side="left", padx=10, pady=15)
        
        backup_world_btn = ctk.CTkButton(controls_frame, text=self.lang.get("backup_world"), 
                                        command=self.backup_selected_world, width=120)
        backup_world_btn.pack(side="left", padx=10, pady=15)
        
        delete_world_btn = ctk.CTkButton(controls_frame, text=self.lang.get("delete_world"), 
                                        command=self.delete_selected_world, width=120)
        delete_world_btn.pack(side="left", padx=10, pady=15)
        
        open_worlds_folder_btn = ctk.CTkButton(controls_frame, text=self.lang.get("open_worlds_folder"), 
                                              command=self.open_worlds_folder, width=140)
        open_worlds_folder_btn.pack(side="right", padx=10, pady=15)
        
        # Load worlds
        self.refresh_worlds()
    
    def refresh_worlds(self):
        """Refresh the worlds list"""
        # Clear existing widgets
        for widget in self.worlds_scroll_frame.winfo_children():
            widget.destroy()
        
        server_path = self.current_project["path"]
        
        # Find world directories
        world_dirs = []
        for item in server_path.iterdir():
            if item.is_dir():
                # Check if it's a world directory (contains level.dat)
                if (item / "level.dat").exists():
                    world_dirs.append(item)
        
        if not world_dirs:
            ctk.CTkLabel(self.worlds_scroll_frame, text=self.lang.get("no_worlds_found")).pack(pady=50)
            return
        
        self.world_selection = tk.StringVar()
        
        for world_dir in sorted(world_dirs):
            world_frame = ctk.CTkFrame(self.worlds_scroll_frame)
            world_frame.pack(fill="x", padx=10, pady=5)
            
            # Radio button for selection
            radio = ctk.CTkRadioButton(world_frame, text="", variable=self.world_selection, value=world_dir.name)
            radio.pack(side="left", padx=10, pady=10)
            
            # World info
            info_frame = ctk.CTkFrame(world_frame)
            info_frame.pack(side="left", fill="x", expand=True, padx=10, pady=5)
            
            # World name
            ctk.CTkLabel(info_frame, text=world_dir.name, font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
            
            # World size
            world_size = self.get_directory_size(world_dir)
            size_mb = world_size / (1024 * 1024)
            ctk.CTkLabel(info_frame, text=f"{self.lang.get('world_size')}: {size_mb:.1f} MB", font=ctk.CTkFont(size=12)).pack(anchor="w", padx=10, pady=(0, 10))
    
    def get_directory_size(self, directory):
        """Calculate total size of directory"""
        total_size = 0
        try:
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        except Exception:
            pass
        return total_size
    
    def backup_selected_world(self):
        """Create a backup of the selected world"""
        if not hasattr(self, 'world_selection') or not self.world_selection.get():
            messagebox.showwarning(self.lang.get("warning"), self.lang.get("no_world_selected"))
            return
        
        world_name = self.world_selection.get()
        world_path = self.current_project["path"] / world_name
        
        # Choose backup location
        backup_path = filedialog.asksaveasfilename(
            title=self.lang.get("save_backup"),
            defaultextension=".zip",
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")],
            initialvalue=f"{world_name}_backup.zip"
        )
        
        if backup_path:
            try:
                import shutil
                shutil.make_archive(backup_path[:-4], 'zip', world_path)
                messagebox.showinfo(self.lang.get("success"), self.lang.get("backup_created"))
            except Exception as e:
                messagebox.showerror(self.lang.get("error"), f"Failed to create backup: {e}")
    
    def delete_selected_world(self):
        """Delete the selected world"""
        if not hasattr(self, 'world_selection') or not self.world_selection.get():
            messagebox.showwarning(self.lang.get("warning"), self.lang.get("no_world_selected"))
            return
        
        world_name = self.world_selection.get()
        
        if messagebox.askyesno(self.lang.get("confirm"), self.lang.get("confirm_delete_world", world_name)):
            world_path = self.current_project["path"] / world_name
            
            try:
                import shutil
                shutil.rmtree(world_path)
                messagebox.showinfo(self.lang.get("success"), self.lang.get("world_deleted"))
                self.refresh_worlds()
            except Exception as e:
                messagebox.showerror(self.lang.get("error"), f"Failed to delete world: {e}")
    
    def open_worlds_folder(self):
        """Open the server directory (where worlds are stored)"""
        server_path = self.current_project["path"]
        
        import subprocess
        import platform
        
        try:
            if platform.system() == "Windows":
                os.startfile(server_path)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", server_path])
            else:  # Linux
                subprocess.run(["xdg-open", server_path])
        except Exception as e:
            messagebox.showerror(self.lang.get("error"), f"Failed to open server folder: {e}")
    
    def import_world(self):
        """Import a world from a zip file or folder"""
        # Ask user to select world source
        choice = messagebox.askyesnocancel(
            self.lang.get("import_world"),
            self.lang.get("select_import_type")
        )
        
        if choice is None:  # Cancel
            return
        elif choice:  # Yes - Import from ZIP
            self.import_world_from_zip()
        else:  # No - Import from folder
            self.import_world_from_folder()
    
    def import_world_from_zip(self):
        """Import world from ZIP file"""
        zip_path = filedialog.askopenfilename(
            title=self.lang.get("select_world_zip"),
            filetypes=[("ZIP files", "*.zip"), ("All files", "*.*")]
        )
        
        if zip_path:
            import zipfile
            import tempfile
            
            try:
                # Extract to temporary directory first
                with tempfile.TemporaryDirectory() as temp_dir:
                    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # Find the world folder (contains level.dat)
                    world_dir = None
                    temp_path = Path(temp_dir)
                    
                    # Check if level.dat is in root of extraction
                    if (temp_path / "level.dat").exists():
                        world_dir = temp_path
                    else:
                        # Look for level.dat in subdirectories
                        for item in temp_path.iterdir():
                            if item.is_dir() and (item / "level.dat").exists():
                                world_dir = item
                                break
                    
                    if not world_dir:
                        messagebox.showerror(self.lang.get("error"), self.lang.get("invalid_world_zip"))
                        return
                    
                    # Ask for world name
                    world_name = simpledialog.askstring(
                        self.lang.get("import_world"),
                        self.lang.get("enter_world_name"),
                        initialvalue=world_dir.name
                    )
                    
                    if not world_name:
                        return
                    
                    # Copy world to server directory
                    server_path = self.current_project["path"]
                    destination = server_path / world_name
                    
                    if destination.exists():
                        if not messagebox.askyesno(self.lang.get("confirm"), self.lang.get("world_exists_overwrite", world_name)):
                            return
                        import shutil
                        shutil.rmtree(destination)
                    
                    import shutil
                    shutil.copytree(world_dir, destination)
                    
                    messagebox.showinfo(self.lang.get("success"), self.lang.get("world_imported", world_name))
                    self.refresh_worlds()
                    
            except Exception as e:
                messagebox.showerror(self.lang.get("error"), f"Failed to import world: {e}")
    
    def import_world_from_folder(self):
        """Import world from existing folder"""
        folder_path = filedialog.askdirectory(
            title=self.lang.get("select_world_folder")
        )
        
        if folder_path:
            world_path = Path(folder_path)
            
            # Verify it's a valid world
            if not (world_path / "level.dat").exists():
                messagebox.showerror(self.lang.get("error"), self.lang.get("invalid_world_folder"))
                return
            
            # Ask for world name
            world_name = simpledialog.askstring(
                self.lang.get("import_world"),
                self.lang.get("enter_world_name"),
                initialvalue=world_path.name
            )
            
            if not world_name:
                return
            
            # Copy world to server directory
            server_path = self.current_project["path"]
            destination = server_path / world_name
            
            if destination.exists():
                if not messagebox.askyesno(self.lang.get("confirm"), self.lang.get("world_exists_overwrite", world_name)):
                    return
                import shutil
                shutil.rmtree(destination)
            
            import shutil
            shutil.copytree(world_path, destination)
            
            messagebox.showinfo(self.lang.get("success"), self.lang.get("world_imported", world_name))
            self.refresh_worlds()
    
    def create_server_console_tab(self, notebook):
        """Create the server console/command interface tab"""
        console_tab = notebook.add(self.lang.get("server_console"))
        
        # Main scrollable container  
        console_container = ctk.CTkScrollableFrame(console_tab, width=750, height=550)
        console_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Server Status Section
        status_frame = ctk.CTkFrame(console_container)
        status_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(status_frame, text=self.lang.get("server_status"), 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        # Server control buttons
        control_frame = ctk.CTkFrame(status_frame)
        control_frame.pack(fill="x", padx=20, pady=10)
        
        self.start_server_btn = ctk.CTkButton(control_frame, text=self.lang.get("start_server"), 
                                             command=self.start_server, width=100, fg_color="green")
        self.start_server_btn.pack(side="left", padx=10, pady=10)
        
        self.stop_server_btn = ctk.CTkButton(control_frame, text=self.lang.get("stop_server"), 
                                            command=self.stop_server, width=100, fg_color="red", state="disabled")
        self.stop_server_btn.pack(side="left", padx=10, pady=10)
        
        self.restart_server_btn = ctk.CTkButton(control_frame, text=self.lang.get("restart_server"), 
                                               command=self.restart_server, width=100, state="disabled")
        self.restart_server_btn.pack(side="left", padx=10, pady=10)
        
        # Status indicator
        self.server_status_label = ctk.CTkLabel(control_frame, text=self.lang.get("server_stopped"), 
                                               text_color="red", font=ctk.CTkFont(size=14, weight="bold"))
        self.server_status_label.pack(side="right", padx=20, pady=10)
        
        # Console Output Section
        output_frame = ctk.CTkFrame(console_container)
        output_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(output_frame, text=self.lang.get("console_output"), 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        # Console output text area
        console_output_frame = ctk.CTkFrame(output_frame)
        console_output_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.console_output = ctk.CTkTextbox(console_output_frame, width=700, height=250, font=ctk.CTkFont(family="Consolas"))
        self.console_output.pack(fill="both", expand=True, padx=10, pady=10)
        self.console_output.insert("0.0", self.lang.get("console_ready"))
        
        # Make console read-only
        self.console_output.configure(state="disabled")
        
        # Command Input Section
        command_frame = ctk.CTkFrame(output_frame)
        command_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(command_frame, text=self.lang.get("send_command")).pack(side="left", padx=10, pady=10)
        
        self.command_entry = ctk.CTkEntry(command_frame, placeholder_text=self.lang.get("enter_command"), width=400)
        self.command_entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.command_entry.bind("<Return>", self.send_command_enter)
        
        self.send_command_btn = ctk.CTkButton(command_frame, text=self.lang.get("send"), 
                                             command=self.send_command, width=80, state="disabled")
        self.send_command_btn.pack(side="right", padx=10, pady=10)
        
        # Quick Commands Section
        quick_commands_frame = ctk.CTkFrame(console_container)
        quick_commands_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(quick_commands_frame, text=self.lang.get("quick_commands"), 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        quick_btns_frame = ctk.CTkFrame(quick_commands_frame)
        quick_btns_frame.pack(fill="x", padx=20, pady=10)
        
        # Common server commands
        quick_commands = [
            ("list", self.lang.get("list_players")),
            ("save-all", self.lang.get("save_world")),
            ("weather clear", self.lang.get("clear_weather")),
            ("time set day", self.lang.get("set_day")),
            ("gamemode creative @a", self.lang.get("creative_all")),
            ("gamemode survival @a", self.lang.get("survival_all"))
        ]
        
        row = 0
        for i, (cmd, label) in enumerate(quick_commands):
            if i % 3 == 0 and i > 0:
                row += 1
            
            btn = ctk.CTkButton(quick_btns_frame, text=label, 
                               command=lambda c=cmd: self.send_quick_command(c), width=150)
            btn.grid(row=row, column=i % 3, padx=5, pady=5, sticky="w")
        
        # Initialize server process variable
        self.server_process = None
        
        # Check for existing running server
        self.check_existing_server_status()
    
    def create_player_management_tab(self, notebook):
        """Create the player management tab"""
        player_tab = notebook.add(self.lang.get("players"))
        
        # Main scrollable container
        main_container = ctk.CTkScrollableFrame(player_tab, width=750, height=550)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Operators (Ops) Section
        ops_frame = ctk.CTkFrame(main_container)
        ops_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(ops_frame, text=self.lang.get("server_operators"), 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        # Ops list with avatars
        ops_list_frame = ctk.CTkScrollableFrame(ops_frame, height=150)
        ops_list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.ops_list_container = ops_list_frame
        
        # Ops controls
        ops_controls = ctk.CTkFrame(ops_frame)
        ops_controls.pack(fill="x", padx=20, pady=10)
        
        self.ops_entry = ctk.CTkEntry(ops_controls, placeholder_text=self.lang.get("enter_username"), width=200)
        self.ops_entry.pack(side="left", padx=10, pady=10)
        
        add_op_btn = ctk.CTkButton(ops_controls, text=self.lang.get("add_operator"), 
                                  command=self.add_operator, width=100)
        add_op_btn.pack(side="left", padx=5, pady=10)
        
        
        # Whitelist Section
        whitelist_frame = ctk.CTkFrame(main_container)
        whitelist_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(whitelist_frame, text=self.lang.get("whitelist"), 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        # Whitelist list with avatars
        whitelist_list_frame = ctk.CTkScrollableFrame(whitelist_frame, height=150)
        whitelist_list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.whitelist_list_container = whitelist_list_frame
        
        # Whitelist controls
        whitelist_controls = ctk.CTkFrame(whitelist_frame)
        whitelist_controls.pack(fill="x", padx=20, pady=10)
        
        # Whitelist status and toggle
        whitelist_status_frame = ctk.CTkFrame(whitelist_controls)
        whitelist_status_frame.pack(fill="x", pady=(0, 10))
        
        self.whitelist_enabled_var = tk.BooleanVar()
        self.whitelist_enabled_checkbox = ctk.CTkCheckBox(whitelist_status_frame, 
                                                         text=self.lang.get("whitelist_enabled"), 
                                                         variable=self.whitelist_enabled_var,
                                                         command=self.toggle_whitelist)
        self.whitelist_enabled_checkbox.pack(side="left", padx=10, pady=10)
        
        self.whitelist_status_label = ctk.CTkLabel(whitelist_status_frame, 
                                                  text=self.lang.get("whitelist_status_checking"),
                                                  font=ctk.CTkFont(size=12))
        self.whitelist_status_label.pack(side="right", padx=10, pady=10)
        
        # Player entry controls
        whitelist_entry_frame = ctk.CTkFrame(whitelist_controls)
        whitelist_entry_frame.pack(fill="x")
        
        self.whitelist_entry = ctk.CTkEntry(whitelist_entry_frame, placeholder_text=self.lang.get("enter_username"), width=200)
        self.whitelist_entry.pack(side="left", padx=10, pady=10)
        
        add_whitelist_btn = ctk.CTkButton(whitelist_entry_frame, text=self.lang.get("add_to_whitelist"), 
                                         command=self.add_to_whitelist, width=120)
        add_whitelist_btn.pack(side="left", padx=5, pady=10)
        
        
        # Blacklist Section  
        blacklist_frame = ctk.CTkFrame(main_container)
        blacklist_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(blacklist_frame, text=self.lang.get("banned_players"), 
                    font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=(20, 10))
        
        # Blacklist list with avatars
        blacklist_list_frame = ctk.CTkScrollableFrame(blacklist_frame, height=150)
        blacklist_list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.blacklist_list_container = blacklist_list_frame
        
        # Blacklist controls
        blacklist_controls = ctk.CTkFrame(blacklist_frame)
        blacklist_controls.pack(fill="x", padx=20, pady=10)
        
        self.blacklist_entry = ctk.CTkEntry(blacklist_controls, placeholder_text=self.lang.get("enter_username"), width=200)
        self.blacklist_entry.pack(side="left", padx=10, pady=10)
        
        add_blacklist_btn = ctk.CTkButton(blacklist_controls, text=self.lang.get("ban_player"), 
                                         command=self.ban_player, width=100)
        add_blacklist_btn.pack(side="left", padx=5, pady=10)
        
        
        # Initialize player data storage
        self.ops_players = []
        self.whitelist_players = []
        self.banned_players = []
        
        # Load existing data
        self.load_player_data()
        
        # Update whitelist status
        self.update_whitelist_status()
    
    def load_player_data(self):
        """Load ops, whitelist, and banned players with avatars"""
        # Clear existing player widgets
        self.clear_player_widgets()
        
        # Load ops
        ops_file = self.current_project["path"] / "ops.json"
        if ops_file.exists():
            try:
                with open(ops_file, 'r') as f:
                    ops_data = json.load(f)
                    for op in ops_data:
                        self.add_player_widget(self.ops_list_container, op.get("name", "Unknown"), "ops")
            except Exception as e:
                print(f"Error loading ops: {e}")
        
        # Load whitelist
        whitelist_file = self.current_project["path"] / "whitelist.json"
        if whitelist_file.exists():
            try:
                with open(whitelist_file, 'r') as f:
                    whitelist_data = json.load(f)
                    for player in whitelist_data:
                        self.add_player_widget(self.whitelist_list_container, player.get("name", "Unknown"), "whitelist")
            except Exception as e:
                print(f"Error loading whitelist: {e}")
        
        # Load banned players
        banned_file = self.current_project["path"] / "banned-players.json"
        if banned_file.exists():
            try:
                with open(banned_file, 'r') as f:
                    banned_data = json.load(f)
                    for player in banned_data:
                        self.add_player_widget(self.blacklist_list_container, player.get("name", "Unknown"), "banned")
            except Exception as e:
                print(f"Error loading banned players: {e}")
        
        # Check whitelist status from server.properties
        self.load_whitelist_status_from_properties()
    
    def clear_player_widgets(self):
        """Clear all player widgets from containers"""
        for widget in self.ops_list_container.winfo_children():
            widget.destroy()
        for widget in self.whitelist_list_container.winfo_children():
            widget.destroy()
        for widget in self.blacklist_list_container.winfo_children():
            widget.destroy()
        
        # Clear player data
        self.ops_players.clear()
        self.whitelist_players.clear()
        self.banned_players.clear()
    
    def get_player_avatar(self, username):
        """Get player avatar from mc-heads.net API"""
        try:
            url = f"https://mc-heads.net/avatar/{username}/32"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                image_data = io.BytesIO(response.content)
                pil_image = Image.open(image_data)
                return ImageTk.PhotoImage(pil_image)
        except Exception as e:
            print(f"Failed to load avatar for {username}: {e}")
        
        # Return default avatar on failure
        try:
            # Create a simple default avatar (gray square)
            default_img = Image.new('RGBA', (32, 32), (128, 128, 128, 255))
            return ImageTk.PhotoImage(default_img)
        except:
            return None
    
    def add_player_widget(self, container, username, player_type):
        """Add a player widget with avatar to the specified container"""
        player_frame = ctk.CTkFrame(container)
        player_frame.pack(fill="x", padx=5, pady=2)
        
        # Get avatar in background thread
        def load_avatar():
            avatar = self.get_player_avatar(username)
            if avatar:
                avatar_label.configure(image=avatar)
                avatar_label.image = avatar  # Keep reference
        
        # Avatar placeholder
        avatar_label = tk.Label(player_frame, width=32, height=32, bg="gray")
        avatar_label.pack(side="left", padx=5, pady=5)
        
        # Username label
        name_label = ctk.CTkLabel(player_frame, text=username, font=ctk.CTkFont(size=12))
        name_label.pack(side="left", padx=10, pady=5)
        
        # Remove button
        remove_btn = ctk.CTkButton(
            player_frame, 
            text="Remove", 
            width=60, 
            height=24,
            command=lambda: self.remove_player_widget(player_frame, username, player_type)
        )
        remove_btn.pack(side="right", padx=5, pady=5)
        
        # Store player data
        if player_type == "ops":
            self.ops_players.append(username)
        elif player_type == "whitelist":
            self.whitelist_players.append(username)
        elif player_type == "banned":
            self.banned_players.append(username)
        
        # Load avatar in background
        threading.Thread(target=load_avatar, daemon=True).start()
    
    def remove_player_widget(self, widget, username, player_type):
        """Remove a player widget and update data"""
        widget.destroy()
        
        # Remove from player data
        if player_type == "ops" and username in self.ops_players:
            self.ops_players.remove(username)
            self.save_ops()
            self.apply_op_to_server(username, False)
        elif player_type == "whitelist" and username in self.whitelist_players:
            self.whitelist_players.remove(username)
            self.save_whitelist()
            self.update_whitelist_status()
            if len(self.whitelist_players) == 0:
                self.auto_disable_whitelist()
            self.apply_whitelist_to_server(username, False)
        elif player_type == "banned" and username in self.banned_players:
            self.banned_players.remove(username)
            self.save_banned_players()
            self.apply_ban_to_server(username, False)
    
    def add_operator(self):
        """Add a player to operators"""
        username = self.ops_entry.get().strip()
        if not username:
            return
        
        # Check if already exists
        if username in self.ops_players:
            messagebox.showwarning(self.lang.get("warning"), self.lang.get("player_already_op", username))
            return
        
        # Add player widget
        self.add_player_widget(self.ops_list_container, username, "ops")
        self.ops_entry.delete(0, tk.END)
        
        # Save to ops.json
        self.save_ops()
        
        # Apply to running server immediately
        self.apply_op_to_server(username, True)
    
    def add_to_whitelist(self):
        """Add player to whitelist"""
        username = self.whitelist_entry.get().strip()
        if not username:
            return
        
        # Check if already exists
        if username in self.whitelist_players:
            messagebox.showwarning(self.lang.get("warning"), self.lang.get("player_already_whitelisted", username))
            return
        
        # Add player widget
        self.add_player_widget(self.whitelist_list_container, username, "whitelist")
        self.whitelist_entry.delete(0, tk.END)
        self.save_whitelist()
        
        # Update whitelist status and auto-enable if this is the first player
        self.update_whitelist_status()
        if len(self.whitelist_players) == 1:  # First player added
            self.auto_enable_whitelist()
        
        # Apply to running server immediately
        self.apply_whitelist_to_server(username, True)
    
    def ban_player(self):
        """Ban a player"""
        username = self.blacklist_entry.get().strip()
        if not username:
            return
        
        # Check if already banned
        if username in self.banned_players:
            messagebox.showwarning(self.lang.get("warning"), self.lang.get("player_already_banned", username))
            return
        
        # Add player widget
        self.add_player_widget(self.blacklist_list_container, username, "banned")
        self.blacklist_entry.delete(0, tk.END)
        self.save_banned_players()
        
        # Apply to running server immediately
        self.apply_ban_to_server(username, True)
    
    def save_ops(self):
        """Save operators to ops.json"""
        ops_data = []
        for username in self.ops_players:
            ops_data.append({
                "uuid": "00000000-0000-0000-0000-000000000000",  # Placeholder UUID
                "name": username,
                "level": 4,
                "bypassesPlayerLimit": False
            })
        
        ops_file = self.current_project["path"] / "ops.json"
        try:
            with open(ops_file, 'w') as f:
                json.dump(ops_data, f, indent=2)
        except Exception as e:
            messagebox.showerror(self.lang.get("error"), f"Failed to save ops: {e}")
    
    def save_whitelist(self):
        """Save whitelist to whitelist.json"""
        whitelist_data = []
        for username in self.whitelist_players:
            whitelist_data.append({
                "uuid": "00000000-0000-0000-0000-000000000000",  # Placeholder UUID
                "name": username
            })
        
        whitelist_file = self.current_project["path"] / "whitelist.json"
        try:
            with open(whitelist_file, 'w') as f:
                json.dump(whitelist_data, f, indent=2)
        except Exception as e:
            messagebox.showerror(self.lang.get("error"), f"Failed to save whitelist: {e}")
    
    def save_banned_players(self):
        """Save banned players to banned-players.json"""
        banned_data = []
        for username in self.banned_players:
            banned_data.append({
                "uuid": "00000000-0000-0000-0000-000000000000",  # Placeholder UUID
                "name": username,
                "created": "2024-01-01 00:00:00 +0000",
                "source": "Server",
                "expires": "forever",
                "reason": "Banned by server administrator"
            })
        
        banned_file = self.current_project["path"] / "banned-players.json"
        try:
            with open(banned_file, 'w') as f:
                json.dump(banned_data, f, indent=2)
        except Exception as e:
            messagebox.showerror(self.lang.get("error"), f"Failed to save banned players: {e}")
    
    def start_server(self):
        """Start the Minecraft server"""
        if self.server_process and self.server_process.poll() is None:
            messagebox.showwarning(self.lang.get("warning"), self.lang.get("server_already_running"))
            return
        
        server_path = self.current_project["path"]
        jar_files = list(server_path.glob("*.jar"))
        
        if not jar_files:
            messagebox.showerror(self.lang.get("error"), self.lang.get("no_server_jar"))
            return
        
        # Use the first jar file found
        jar_file = jar_files[0]
        
        try:
            import subprocess
            import os
            
            # Start server process
            cmd = ["java", "-Xmx2G", "-Xms2G", "-jar", jar_file.name, "nogui"]
            
            self.server_process = subprocess.Popen(
                cmd,
                cwd=server_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Save server status to file
            self.save_server_status()
            
            # Update UI
            self.start_server_btn.configure(state="disabled")
            self.stop_server_btn.configure(state="normal")
            self.restart_server_btn.configure(state="normal")
            self.send_command_btn.configure(state="normal")
            self.server_status_label.configure(text=self.lang.get("server_starting"), text_color="orange")
            
            # Start reading server output
            self.read_server_output()
            
            self.console_output.insert("end", f"\n[{self.get_timestamp()}] {self.lang.get('server_started')}\n")
            self.console_output.see("end")
            
        except Exception as e:
            messagebox.showerror(self.lang.get("error"), f"Failed to start server: {e}")
    
    def stop_server(self):
        """Stop the Minecraft server"""
        if not self.server_process or self.server_process.poll() is not None:
            messagebox.showwarning(self.lang.get("warning"), self.lang.get("server_not_running"))
            return
        
        try:
            # Check if this is a reconnected server (ProcessWrapper)
            if hasattr(self.server_process, '_process') and not hasattr(self.server_process, 'stdin'):
                # This is a reconnected server, we can only terminate it
                messagebox.showinfo(self.lang.get("info"), self.lang.get("reconnected_server_force_stop"))
                self.server_process.kill()
                
                # Update UI immediately
                self.start_server_btn.configure(state="normal")
                self.stop_server_btn.configure(state="disabled")
                self.restart_server_btn.configure(state="disabled")
                self.send_command_btn.configure(state="disabled")
                self.server_status_label.configure(text=self.lang.get("server_stopped"), text_color="red")
                
                # Clear server status file
                self.clear_server_status()
                
                self.console_output.insert("end", f"\n[{self.get_timestamp()}] {self.lang.get('server_force_stopped')}\n")
                self.console_output.see("end")
                return
            
            # Normal server stop process
            if hasattr(self.server_process, 'stdin') and self.server_process.stdin:
                # Send stop command
                self.server_process.stdin.write("stop\n")
                self.server_process.stdin.flush()
                
                # Wait for process to terminate
                self.server_process.wait(timeout=30)
            else:
                # Fallback to termination
                self.server_process.kill()
            
            # Update UI
            self.start_server_btn.configure(state="normal")
            self.stop_server_btn.configure(state="disabled")
            self.restart_server_btn.configure(state="disabled")
            self.send_command_btn.configure(state="disabled")
            self.server_status_label.configure(text=self.lang.get("server_stopped"), text_color="red")
            
            # Clear server status file
            self.clear_server_status()
            
            self.console_output.insert("end", f"\n[{self.get_timestamp()}] {self.lang.get('server_stopped')}\n")
            self.console_output.see("end")
            
        except subprocess.TimeoutExpired:
            # Force kill if stop command doesn't work
            self.server_process.kill()
            messagebox.showwarning(self.lang.get("warning"), self.lang.get("server_force_stopped"))
            
            # Update UI
            self.start_server_btn.configure(state="normal")
            self.stop_server_btn.configure(state="disabled")
            self.restart_server_btn.configure(state="disabled")
            self.send_command_btn.configure(state="disabled")
            self.server_status_label.configure(text=self.lang.get("server_stopped"), text_color="red")
            
            # Clear server status file
            self.clear_server_status()
            
        except Exception as e:
            messagebox.showerror(self.lang.get("error"), f"Failed to stop server: {e}")
            # Try force kill as last resort
            try:
                self.server_process.kill()
                self.clear_server_status()
            except:
                pass
    
    def restart_server(self):
        """Restart the Minecraft server"""
        self.console_output.insert("end", f"\n[{self.get_timestamp()}] {self.lang.get('server_restarting')}\n")
        self.console_output.see("end")
        
        self.stop_server()
        # Wait a moment before restarting
        self.root.after(2000, self.start_server)
    
    def send_command(self):
        """Send command to server"""
        command = self.command_entry.get().strip()
        if not command:
            return
        
        self.send_server_command(command)
        self.command_entry.delete(0, 'end')
    
    def send_command_enter(self, event):
        """Send command when Enter is pressed"""
        self.send_command()
    
    def send_quick_command(self, command):
        """Send a quick command to the server"""
        self.send_server_command(command)
    
    def send_server_command(self, command):
        """Send command to the running server"""
        if not self.server_process or self.server_process.poll() is not None:
            messagebox.showwarning(self.lang.get("warning"), self.lang.get("server_not_running"))
            return
        
        # Check if this is a reconnected server without stdin access
        if hasattr(self.server_process, '_process') and not hasattr(self.server_process, 'stdin'):
            messagebox.showwarning(self.lang.get("warning"), self.lang.get("reconnected_server_no_commands"))
            return
        
        try:
            if hasattr(self.server_process, 'stdin') and self.server_process.stdin:
                self.server_process.stdin.write(f"{command}\n")
                self.server_process.stdin.flush()
                
                # Log command in console
                self.console_output.insert("end", f"\n[{self.get_timestamp()}] > {command}\n")
                self.console_output.see("end")
            else:
                messagebox.showwarning(self.lang.get("warning"), self.lang.get("server_command_unavailable"))
            
        except Exception as e:
            messagebox.showerror(self.lang.get("error"), f"Failed to send command: {e}")
    
    def read_server_output(self):
        """Read server output continuously"""
        if not self.server_process:
            return
        
        def read_output():
            while self.server_process and self.server_process.poll() is None:
                try:
                    line = self.server_process.stdout.readline()
                    if line:
                        self.root.after(0, lambda: self.append_console_output(line.strip()))
                except:
                    break
            
            # Server has stopped
            if self.server_process:
                self.root.after(0, self.on_server_stopped)
        
        import threading
        threading.Thread(target=read_output, daemon=True).start()
    
    def append_console_output(self, text):
        """Append text to console output"""
        # Temporarily enable the textbox to add text
        self.console_output.configure(state="normal")
        self.console_output.insert("end", f"\n[{self.get_timestamp()}] {text}")
        self.console_output.see("end")
        # Disable the textbox again to maintain read-only state
        self.console_output.configure(state="disabled")
        
        # Update server status based on output
        if "Done" in text and "For help" in text:
            self.server_status_label.configure(text=self.lang.get("server_running"), text_color="green")
    
    def on_server_stopped(self):
        """Handle server stop event"""
        self.start_server_btn.configure(state="normal")
        self.stop_server_btn.configure(state="disabled")
        self.restart_server_btn.configure(state="disabled")
        self.send_command_btn.configure(state="disabled")
        self.server_status_label.configure(text=self.lang.get("server_stopped"), text_color="red")
        
        # Clear server status file
        self.clear_server_status()
    
    def get_timestamp(self):
        """Get current timestamp for console messages"""
        import datetime
        return datetime.datetime.now().strftime("%H:%M:%S")
    
    def apply_op_to_server(self, username, is_add):
        """Apply operator change to running server"""
        if not self.server_process or self.server_process.poll() is not None:
            # Server not running, show info message
            action = self.lang.get("added_to_ops") if is_add else self.lang.get("removed_from_ops")
            messagebox.showinfo(self.lang.get("info"), self.lang.get("player_change_saved", username, action))
            return
        
        try:
            if is_add:
                command = f"op {username}"
                action_msg = self.lang.get("opped_player", username)
            else:
                command = f"deop {username}"
                action_msg = self.lang.get("deopped_player", username)
            
            # Send command to server
            self.server_process.stdin.write(f"{command}\n")
            self.server_process.stdin.flush()
            
            # Log in console
            self.console_output.insert("end", f"\n[{self.get_timestamp()}] > {command}")
            self.console_output.insert("end", f"\n[{self.get_timestamp()}] {action_msg}")
            self.console_output.see("end")
            
            # Show success message
            messagebox.showinfo(self.lang.get("success"), action_msg)
            
        except Exception as e:
            messagebox.showerror(self.lang.get("error"), f"Failed to apply operator change: {e}")
    
    def apply_whitelist_to_server(self, username, is_add):
        """Apply whitelist change to running server"""
        if not self.server_process or self.server_process.poll() is not None:
            # Server not running, show info message
            action = self.lang.get("added_to_whitelist") if is_add else self.lang.get("removed_from_whitelist_action")
            messagebox.showinfo(self.lang.get("info"), self.lang.get("player_change_saved", username, action))
            return
        
        try:
            if is_add:
                command = f"whitelist add {username}"
                action_msg = self.lang.get("whitelisted_player", username)
            else:
                command = f"whitelist remove {username}"
                action_msg = self.lang.get("removed_whitelist_player", username)
            
            # Send command to server
            self.server_process.stdin.write(f"{command}\n")
            self.server_process.stdin.flush()
            
            # Log in console
            self.console_output.insert("end", f"\n[{self.get_timestamp()}] > {command}")
            self.console_output.insert("end", f"\n[{self.get_timestamp()}] {action_msg}")
            self.console_output.see("end")
            
            # Show success message
            messagebox.showinfo(self.lang.get("success"), action_msg)
            
        except Exception as e:
            messagebox.showerror(self.lang.get("error"), f"Failed to apply whitelist change: {e}")
    
    def apply_ban_to_server(self, username, is_ban):
        """Apply ban change to running server"""
        if not self.server_process or self.server_process.poll() is not None:
            # Server not running, show info message
            action = self.lang.get("banned") if is_ban else self.lang.get("unbanned")
            messagebox.showinfo(self.lang.get("info"), self.lang.get("player_change_saved", username, action))
            return
        
        try:
            if is_ban:
                command = f"ban {username}"
                action_msg = self.lang.get("banned_player", username)
            else:
                command = f"pardon {username}"
                action_msg = self.lang.get("unbanned_player", username)
            
            # Send command to server
            self.server_process.stdin.write(f"{command}\n")
            self.server_process.stdin.flush()
            
            # Log in console
            self.console_output.insert("end", f"\n[{self.get_timestamp()}] > {command}")
            self.console_output.insert("end", f"\n[{self.get_timestamp()}] {action_msg}")
            self.console_output.see("end")
            
            # Show success message
            messagebox.showinfo(self.lang.get("success"), action_msg)
            
        except Exception as e:
            messagebox.showerror(self.lang.get("error"), f"Failed to apply ban change: {e}")
    
    def load_whitelist_status_from_properties(self):
        """Load whitelist enabled status from server.properties"""
        try:
            properties_file = self.current_project["path"] / "server.properties"
            if properties_file.exists():
                with open(properties_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('white-list='):
                            value = line.split('=', 1)[1].strip().lower()
                            self.whitelist_enabled_var.set(value == 'true')
                            return
            
            # Default to false if not found
            self.whitelist_enabled_var.set(False)
            
        except Exception as e:
            print(f"Error loading whitelist status: {e}")
            self.whitelist_enabled_var.set(False)
    
    def update_whitelist_status(self):
        """Update whitelist status display"""
        player_count = len(self.whitelist_players)
        is_enabled = self.whitelist_enabled_var.get()
        
        if is_enabled:
            if player_count > 0:
                status_text = self.lang.get("whitelist_active_players", player_count)
                status_color = "green"
            else:
                status_text = self.lang.get("whitelist_active_no_players")
                status_color = "orange"
        else:
            if player_count > 0:
                status_text = self.lang.get("whitelist_disabled_has_players", player_count)
                status_color = "gray"
            else:
                status_text = self.lang.get("whitelist_disabled_empty")
                status_color = "gray"
        
        self.whitelist_status_label.configure(text=status_text, text_color=status_color)
    
    def toggle_whitelist(self):
        """Toggle whitelist enabled/disabled"""
        is_enabled = self.whitelist_enabled_var.get()
        
        # Update server.properties
        self.update_whitelist_in_properties(is_enabled)
        
        # Apply to running server
        self.apply_whitelist_toggle_to_server(is_enabled)
        
        # Update status display
        self.update_whitelist_status()
    
    def auto_enable_whitelist(self):
        """Automatically enable whitelist when first player is added"""
        if not self.whitelist_enabled_var.get():
            self.whitelist_enabled_var.set(True)
            self.update_whitelist_in_properties(True)
            self.apply_whitelist_toggle_to_server(True)
            
            # Show info message
            messagebox.showinfo(self.lang.get("info"), self.lang.get("whitelist_auto_enabled"))
    
    def auto_disable_whitelist(self):
        """Automatically disable whitelist when last player is removed"""
        if self.whitelist_enabled_var.get():
            result = messagebox.askyesno(
                self.lang.get("confirm"), 
                self.lang.get("whitelist_auto_disable_confirm")
            )
            
            if result:
                self.whitelist_enabled_var.set(False)
                self.update_whitelist_in_properties(False)
                self.apply_whitelist_toggle_to_server(False)
                
                messagebox.showinfo(self.lang.get("info"), self.lang.get("whitelist_auto_disabled"))
    
    def update_whitelist_in_properties(self, enabled):
        """Update whitelist setting in server.properties"""
        try:
            properties_file = self.current_project["path"] / "server.properties"
            
            # Read existing properties
            properties = {}
            if properties_file.exists():
                with open(properties_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            properties[key.strip()] = value.strip()
            
            # Update whitelist setting
            properties['white-list'] = 'true' if enabled else 'false'
            
            # Write back to file
            with open(properties_file, 'w', encoding='utf-8') as f:
                f.write("#Minecraft server properties\n")
                f.write("#Generated by Minecraft Server Installer\n")
                for key, value in properties.items():
                    f.write(f"{key}={value}\n")
            
        except Exception as e:
            print(f"Error updating server.properties: {e}")
    
    def apply_whitelist_toggle_to_server(self, enabled):
        """Apply whitelist enable/disable to running server"""
        if not self.server_process or self.server_process.poll() is not None:
            return  # Server not running
        
        try:
            command = "whitelist on" if enabled else "whitelist off"
            action_msg = self.lang.get("whitelist_enabled_server") if enabled else self.lang.get("whitelist_disabled_server")
            
            # Send command to server
            self.server_process.stdin.write(f"{command}\n")
            self.server_process.stdin.flush()
            
            # Log in console
            self.console_output.insert("end", f"\n[{self.get_timestamp()}] > {command}")
            self.console_output.insert("end", f"\n[{self.get_timestamp()}] {action_msg}")
            self.console_output.see("end")
            
        except Exception as e:
            print(f"Failed to apply whitelist toggle: {e}")
    
    def save_server_status(self):
        """Save server status and PID to file for persistence"""
        if not self.server_process:
            return
        
        try:
            status_data = {
                "pid": self.server_process.pid,
                "status": "running",
                "started_at": self.get_timestamp(),
                "jar_file": self.get_server_jar_name()
            }
            
            status_file = self.current_project["path"] / ".server_status.json"
            with open(status_file, 'w') as f:
                json.dump(status_data, f, indent=2)
                
        except Exception as e:
            print(f"Failed to save server status: {e}")
    
    def clear_server_status(self):
        """Clear server status file"""
        try:
            status_file = self.current_project["path"] / ".server_status.json"
            if status_file.exists():
                status_file.unlink()
        except Exception as e:
            print(f"Failed to clear server status: {e}")
    
    def check_existing_server_status(self):
        """Check if server is already running when GUI opens"""
        if not hasattr(self, 'current_project') or not self.current_project:
            return
            
        try:
            status_file = self.current_project["path"] / ".server_status.json"
            if not status_file.exists():
                return
            
            with open(status_file, 'r') as f:
                status_data = json.load(f)
            
            pid = status_data.get("pid")
            if not pid:
                self.clear_server_status()
                return
            
            # Check if process is still running
            if self.is_process_running(pid):
                # Server is running, update UI accordingly
                self.reconnect_to_server(pid, status_data)
            else:
                # Process not running, clear stale status
                self.clear_server_status()
                
        except Exception as e:
            print(f"Error checking server status: {e}")
            self.clear_server_status()
    
    def is_process_running(self, pid):
        """Check if a process with given PID is running"""
        try:
            import psutil
            return psutil.pid_exists(pid)
        except ImportError:
            # Fallback method if psutil not available
            try:
                import os
                import signal
                os.kill(pid, 0)
                return True
            except (OSError, ProcessLookupError):
                return False
    
    def reconnect_to_server(self, pid, status_data):
        """Reconnect to existing server process"""
        try:
            # Update UI to show server is running
            if hasattr(self, 'start_server_btn'):
                self.start_server_btn.configure(state="disabled")
                self.stop_server_btn.configure(state="normal") 
                self.restart_server_btn.configure(state="normal")
                self.send_command_btn.configure(state="normal")
                self.server_status_label.configure(text=self.lang.get("server_running"), text_color="green")
            
            # Show reconnection message in console
            if hasattr(self, 'console_output'):
                start_time = status_data.get("started_at", "unknown")
                jar_file = status_data.get("jar_file", "unknown")
                reconnect_msg = self.lang.get("server_reconnected", pid, start_time, jar_file)
                
                self.console_output.insert("end", f"\n[{self.get_timestamp()}] {reconnect_msg}\n")
                self.console_output.see("end")
            
            # Try to reconnect to process for command sending (limited functionality)
            # Note: We can't fully reconnect stdin/stdout, but we can track the process
            try:
                import psutil
                process = psutil.Process(pid)
                # Create a minimal process object for status tracking
                class ProcessWrapper:
                    def __init__(self, pid):
                        self.pid = pid
                        self._process = psutil.Process(pid)
                        # Explicitly indicate this is a reconnected process
                        self._is_reconnected = True
                    
                    def poll(self):
                        try:
                            return None if self._process.is_running() else 0
                        except psutil.NoSuchProcess:
                            return 0
                    
                    def kill(self):
                        try:
                            self._process.terminate()
                        except psutil.NoSuchProcess:
                            pass
                    
                    def wait(self, timeout=None):
                        try:
                            self._process.wait(timeout)
                        except psutil.NoSuchProcess:
                            pass
                    
                    # Note: No stdin/stdout - can't send commands to reconnected process
                
                self.server_process = ProcessWrapper(pid)
                
                # Show warning about limited functionality
                if hasattr(self, 'console_output'):
                    warning_msg = self.lang.get("reconnect_limited_functionality")
                    self.console_output.insert("end", f"\n[{self.get_timestamp()}] ⚠️ {warning_msg}\n")
                    self.console_output.see("end")
                    
            except ImportError:
                # If psutil not available, show message about installing it
                if hasattr(self, 'console_output'):
                    psutil_msg = self.lang.get("install_psutil_for_reconnect")
                    self.console_output.insert("end", f"\n[{self.get_timestamp()}] ℹ️ {psutil_msg}\n")
                    self.console_output.see("end")
                    
        except Exception as e:
            print(f"Error reconnecting to server: {e}")
            self.clear_server_status()
    
    def get_server_jar_name(self):
        """Get the name of the server jar file"""
        try:
            server_path = self.current_project["path"]
            jar_files = list(server_path.glob("*.jar"))
            return jar_files[0].name if jar_files else "unknown"
        except Exception:
            return "unknown"
    
    def is_server_running(self):
        """Check if server is currently running"""
        if hasattr(self, 'server_process') and self.server_process:
            try:
                return self.server_process.poll() is None
            except Exception:
                return False
        return False
    
    def shutdown_server_on_exit(self):
        """Shutdown server gracefully when GUI is closing"""
        if not self.is_server_running():
            return
        
        try:
            # Show shutdown progress
            progress_window = ctk.CTkToplevel(self.root)
            progress_window.title(self.lang.get("shutting_down_server"))
            progress_window.geometry("400x150")
            progress_window.resizable(False, False)
            
            # Center the window
            progress_window.transient(self.root)
            progress_window.grab_set()
            
            # Progress label
            progress_label = ctk.CTkLabel(progress_window, 
                                        text=self.lang.get("shutting_down_server_please_wait"),
                                        font=ctk.CTkFont(size=14))
            progress_label.pack(pady=30)
            
            # Progress bar
            progress_bar = ctk.CTkProgressBar(progress_window, width=300)
            progress_bar.pack(pady=10)
            progress_bar.set(0.3)
            
            # Force update display
            progress_window.update()
            
            # Try graceful shutdown first
            if hasattr(self.server_process, 'stdin') and self.server_process.stdin:
                try:
                    progress_label.configure(text=self.lang.get("sending_stop_command"))
                    progress_bar.set(0.6)
                    progress_window.update()
                    
                    self.server_process.stdin.write("stop\n")
                    self.server_process.stdin.flush()
                    
                    # Wait up to 10 seconds for graceful shutdown
                    import time
                    for i in range(10):
                        if self.server_process.poll() is not None:
                            break
                        time.sleep(1)
                        progress_bar.set(0.6 + (i * 0.03))
                        progress_window.update()
                    
                except Exception as e:
                    print(f"Error during graceful shutdown: {e}")
            
            # Force kill if still running
            if self.server_process.poll() is None:
                progress_label.configure(text=self.lang.get("force_stopping_server"))
                progress_bar.set(0.9)
                progress_window.update()
                
                self.server_process.kill()
                
                # Wait a moment for process to die
                import time
                time.sleep(1)
            
            # Clean up status file
            self.clear_server_status()
            
            progress_bar.set(1.0)
            progress_label.configure(text=self.lang.get("server_shutdown_complete"))
            progress_window.update()
            
            # Close progress window after a brief delay
            import time
            time.sleep(1)
            progress_window.destroy()
            
        except Exception as e:
            print(f"Error shutting down server: {e}")
            # Try force kill as last resort
            try:
                if hasattr(self, 'server_process') and self.server_process:
                    self.server_process.kill()
                self.clear_server_status()
            except Exception:
                pass
    
    def leave_server_running_on_exit(self):
        """Leave server running when GUI closes"""
        try:
            # Show info about reconnection
            messagebox.showinfo(
                self.lang.get("server_left_running"),
                self.lang.get("server_left_running_info")
            )
            
            # Keep the status file so we can reconnect later
            # (Status file is already saved when server started)
            
        except Exception as e:
            print(f"Error in leave_server_running_on_exit: {e}")
        
    def create_widgets(self):
        # Main frame
        main_frame = ctk.CTkScrollableFrame(self.root, width=880, height=680)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Top bar with title and settings
        top_frame = ctk.CTkFrame(main_frame)
        top_frame.pack(fill="x", pady=(0, 20))
        
        # Title
        self.title_label = ctk.CTkLabel(top_frame, text=self.lang.get("title"), 
                                       font=ctk.CTkFont(size=24, weight="bold"))
        self.title_label.pack(side="left", padx=20, pady=20)
        
        # Open Project button
        self.open_project_button = ctk.CTkButton(top_frame, text=self.lang.get("open_server_project"), 
                                                command=self.open_server_project, width=140)
        self.open_project_button.pack(side="right", padx=(0, 10), pady=20)
        
        # Settings button
        self.settings_button = ctk.CTkButton(top_frame, text=self.lang.get("settings"), 
                                           command=self.open_settings, width=100)
        self.settings_button.pack(side="right", padx=20, pady=20)
        
        # Server Path Section
        path_frame = ctk.CTkFrame(main_frame)
        path_frame.pack(fill="x", pady=(0, 20))
        
        self.path_label = ctk.CTkLabel(path_frame, text=self.lang.get("server_path"), 
                                      font=ctk.CTkFont(size=16, weight="bold"))
        self.path_label.pack(anchor="w", padx=20, pady=(20, 10))
        
        path_select_frame = ctk.CTkFrame(path_frame)
        path_select_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.path_entry = ctk.CTkEntry(path_select_frame, textvariable=self.server_path, 
                                      placeholder_text=self.lang.get("select_path"))
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.browse_button = ctk.CTkButton(path_select_frame, text=self.lang.get("browse"), 
                                          command=self.browse_path)
        self.browse_button.pack(side="right")
        
        # Server Core Section
        core_frame = ctk.CTkFrame(main_frame)
        core_frame.pack(fill="x", pady=(0, 20))
        
        self.core_label = ctk.CTkLabel(core_frame, text=self.lang.get("server_core"), 
                                      font=ctk.CTkFont(size=16, weight="bold"))
        self.core_label.pack(anchor="w", padx=20, pady=(20, 10))
        
        core_options = ["Vanilla", "Paper", "Spigot", "Fabric"]
        self.core_menu = ctk.CTkOptionMenu(core_frame, values=core_options, 
                                          variable=self.server_core,
                                          command=self.on_core_change)
        self.core_menu.pack(padx=20, pady=(0, 20))
        
        # Version Section
        version_frame = ctk.CTkFrame(main_frame)
        version_frame.pack(fill="x", pady=(0, 20))
        
        self.version_label = ctk.CTkLabel(version_frame, text=self.lang.get("server_version"), 
                                         font=ctk.CTkFont(size=16, weight="bold"))
        self.version_label.pack(anchor="w", padx=20, pady=(20, 10))
        
        version_select_frame = ctk.CTkFrame(version_frame)
        version_select_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.version_entry = ctk.CTkEntry(version_select_frame, textvariable=self.server_version, 
                                         placeholder_text=self.lang.get("loading"))
        self.version_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.version_button = ctk.CTkButton(version_select_frame, text=self.lang.get("select_version"), 
                                           command=self.open_version_selector, width=120)
        self.version_button.pack(side="right")
        
        # EULA Section
        eula_frame = ctk.CTkFrame(main_frame)
        eula_frame.pack(fill="x", pady=(0, 20))
        
        self.eula_title = ctk.CTkLabel(eula_frame, text=self.lang.get("eula_agreement"), 
                                      font=ctk.CTkFont(size=16, weight="bold"))
        self.eula_title.pack(anchor="w", padx=20, pady=(20, 10))
        
        eula_checkbox_frame = ctk.CTkFrame(eula_frame)
        eula_checkbox_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        self.eula_checkbox = ctk.CTkCheckBox(eula_checkbox_frame, 
                                           text=self.lang.get("accept_eula"), 
                                           variable=self.eula_accepted)
        self.eula_checkbox.pack(side="left", padx=(0, 10))
        
        self.read_eula_button = ctk.CTkButton(eula_checkbox_frame, text=self.lang.get("read_eula"), 
                                             command=self.open_eula)
        self.read_eula_button.pack(side="right")
        
        self.eula_note = ctk.CTkLabel(eula_frame, text=self.lang.get("eula_note"),
                                     font=ctk.CTkFont(size=12))
        self.eula_note.pack(padx=20, pady=(0, 20))
        
        # Progress Section
        self.progress_frame = ctk.CTkFrame(main_frame)
        self.progress_frame.pack(fill="x", pady=(0, 20))
        
        self.progress_label = ctk.CTkLabel(self.progress_frame, text=self.lang.get("ready_to_install"))
        self.progress_label.pack(pady=(20, 10))
        
        self.progress_bar = ctk.CTkProgressBar(self.progress_frame)
        self.progress_bar.pack(fill="x", padx=20, pady=(0, 20))
        self.progress_bar.set(0)
        
        # Install Button
        self.install_button = ctk.CTkButton(main_frame, text=self.lang.get("install_server"), 
                                          command=self.install_server,
                                          font=ctk.CTkFont(size=16, weight="bold"),
                                          height=50)
        self.install_button.pack(pady=20)
        
    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.server_path.set(path)
    
    def on_core_change(self, core):
        self.load_version_data()
    
    def load_version_data(self):
        # Show loading state
        self.show_loading_state(True)
        
        def load_versions():
            try:
                core = self.server_core.get().lower()
                print(f"Loading versions for {core} in background thread...")
                
                # Do all HTTP requests in background thread
                if core == "vanilla":
                    self.load_vanilla_versions_bg()
                elif core == "paper":
                    self.load_paper_versions_bg()
                elif core == "spigot":
                    self.load_spigot_versions_bg()
                elif core == "fabric":
                    self.load_fabric_versions_bg()
                    
                print(f"Finished loading {core} versions")
            except Exception as e:
                print(f"Error loading versions: {e}")
                self.root.after(0, lambda: messagebox.showerror(self.lang.get("error"), self.lang.get("failed_to_load", str(e))))
            finally:
                # Hide loading state on main thread
                self.root.after(0, lambda: self.show_loading_state(False))
        
        threading.Thread(target=load_versions, daemon=True).start()
    
    def show_loading_state(self, loading):
        """Show or hide loading animation"""
        if loading:
            # Disable version selector button
            self.version_button.configure(state="disabled", text=self.lang.get("loading"))
            # Start loading animation
            self.start_loading_animation()
        else:
            # Enable version selector button
            self.version_button.configure(state="normal", text=self.lang.get("select_version"))
            # Stop loading animation
            self.stop_loading_animation()
    
    def start_loading_animation(self):
        """Start a loading animation"""
        self.loading_dots = 0
        self.loading_active = True
        self.animate_loading()
    
    def animate_loading(self):
        """Animate loading dots"""
        if hasattr(self, 'loading_active') and self.loading_active:
            dots = "." * (self.loading_dots % 4)
            self.version_entry.configure(placeholder_text=f"{self.lang.get('loading')}{dots}")
            self.loading_dots += 1
            self.root.after(500, self.animate_loading)
    
    def stop_loading_animation(self):
        """Stop loading animation"""
        self.loading_active = False
    
    def load_vanilla_versions_bg(self):
        """Load vanilla versions in background thread"""
        try:
            response = requests.get("https://piston-meta.mojang.com/mc/game/version_manifest.json")
            data = response.json()
            # Store all versions for the version selector (keep original order - newest first)
            self.all_versions["vanilla"] = data["versions"]
            # Get available versions for quick selection
            releases = [v["id"] for v in data["versions"] if v["type"] == "release"]
            snapshots = [v["id"] for v in data["versions"] if v["type"] == "snapshot"]
            all_versions = releases + snapshots[:10]  # Add recent snapshots
            self.available_versions = all_versions[:50]  # Fixed limit
            self.versions_data = {v["id"]: v for v in data["versions"]}
            print(f"Loaded {len(self.available_versions)} vanilla versions, total available: {len(self.all_versions['vanilla'])}")
            # Update UI on main thread
            self.root.after(0, self.update_version_display)
        except Exception as e:
            print(f"Error loading vanilla versions: {e}")
    
    def load_vanilla_versions(self):
        """Legacy method for backward compatibility"""
        self.load_vanilla_versions_bg()
    
    def load_paper_versions_bg(self):
        """Load paper versions in background thread"""
        try:
            response = requests.get("https://api.papermc.io/v2/projects/paper")
            data = response.json()
            versions = data["versions"][-50:]  # Latest versions based on setting
            self.available_versions = versions[::-1]  # Reverse to show latest first
            # Store all versions for the version selector
            self.all_versions["paper"] = [{"id": v, "type": "release"} for v in data["versions"]]
            # Update UI on main thread
            self.root.after(0, self.update_version_display)
        except Exception as e:
            print(f"Error loading paper versions: {e}")
    
    def load_paper_versions(self):
        """Legacy method for backward compatibility"""
        self.load_paper_versions_bg()
    
    def load_spigot_versions_bg(self):
        """Load spigot versions directly from GetBukkit.org"""
        try:
            print("Loading Spigot versions from GetBukkit.org...")
            response = requests.get("https://getbukkit.org/download/spigot", timeout=30)
            if response.status_code == 200:
                content = response.text
                # 解析頁面中的版本號碼
                spigot_versions = self.parse_spigot_versions_from_page(content)
                
                if spigot_versions:
                    self.available_versions = spigot_versions[:self.max_versions]
                    self.all_versions["spigot"] = [{"id": v, "type": "release"} for v in spigot_versions]
                    print(f"Loaded {len(self.available_versions)} Spigot versions from GetBukkit, total available: {len(spigot_versions)}")
                else:
                    # 如果解析失敗，使用備用版本列表
                    self.use_fallback_spigot_versions()
            else:
                self.use_fallback_spigot_versions()
            
            # Update UI on main thread
            self.root.after(0, self.update_version_display)
            
        except Exception as e:
            print(f"Error loading Spigot versions: {e}")
            self.use_fallback_spigot_versions()
            self.root.after(0, self.update_version_display)
    
    def parse_spigot_versions_from_page(self, content):
        """從 GetBukkit 頁面解析版本號碼"""
        import re
        versions = []
        
        # 尋找版本號碼的模式
        # 在 GetBukkit 頁面中，版本號碼出現在特定位置
        version_patterns = [
            r'(\d+\.\d+(?:\.\d+)?)\s*\n.*?getbukkit\.org/get/',  # 版本號碼後面跟著下載連結
            r'>(\d+\.\d+(?:\.\d+)?)<',  # HTML標籤中的版本號碼
            r'Version[:\s]*(\d+\.\d+(?:\.\d+)?)',  # "Version" 後面的版本號碼
        ]
        
        for pattern in version_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                versions.extend(matches)
        
        # 去除重複並排序
        unique_versions = list(dict.fromkeys(versions))  # 保持順序去重
        
        # 驗證版本格式並過濾
        valid_versions = []
        for version in unique_versions:
            if self.is_valid_minecraft_version(version):
                valid_versions.append(version)
        
        print(f"Parsed versions from GetBukkit: {valid_versions[:10]}...")  # 顯示前10個版本
        return valid_versions
    
    def is_valid_minecraft_version(self, version):
        """檢查是否為有效的 Minecraft 版本格式"""
        import re
        # 匹配格式如 1.8, 1.16.5, 1.21.3 等
        pattern = r'^\d+\.\d+(?:\.\d+)?$'
        if re.match(pattern, version):
            try:
                parts = version.split('.')
                major = int(parts[0])
                minor = int(parts[1])
                # Spigot 支援 1.8 以上版本
                return major > 1 or (major == 1 and minor >= 8)
            except:
                return False
        return False
    
    def use_fallback_spigot_versions(self):
        """使用備用的 Spigot 版本列表"""
        fallback_versions = [
            "1.21.5", "1.21.4", "1.21.3", "1.21.1", "1.21", 
            "1.20.6", "1.20.4", "1.20.2", "1.20.1", "1.20",
            "1.19.4", "1.19.2", "1.19", "1.18.2", "1.18.1", 
            "1.17.1", "1.16.5", "1.16.4", "1.16.3", "1.16.2", "1.16.1",
            "1.15.2", "1.14.4", "1.13.2", "1.13.1", "1.12.2", 
            "1.11.2", "1.10.2", "1.9.4", "1.8.8"
        ]
        self.available_versions = fallback_versions[:self.max_versions]
        self.all_versions["spigot"] = [{"id": v, "type": "release"} for v in fallback_versions]
        print(f"Using fallback Spigot versions: {len(self.available_versions)}")
    
    def is_spigot_version_supported(self, version):
        """檢查 Minecraft 版本是否被 Spigot 支援"""
        return self.is_valid_minecraft_version(version)
    
    def load_spigot_versions(self):
        """Legacy method for backward compatibility"""
        self.load_spigot_versions_bg()
    
    def load_fabric_versions_bg(self):
        """Load fabric versions in background thread using optimized API"""
        try:
            print("Loading Fabric versions using Meta API v1/versions endpoint...")
            
            # Get all version data in a single request - much more efficient!
            api_response = requests.get("https://meta.fabricmc.net/v1/versions")
            api_data = api_response.json()
            
            # Extract game versions (includes all releases and snapshots)
            game_versions = api_data.get("game", [])
            
            # Store fabric metadata for server jar downloads
            self.fabric_metadata = {
                "loader_versions": api_data.get("loader", []),
                "installer_versions": api_data.get("installer", [])
            }
            
            # Process game versions
            all_versions = []
            for v in game_versions:
                version_id = v["version"]
                is_stable = v.get("stable", True)
                
                # Classify version type based on format and stability
                if not is_stable:
                    # Determine snapshot type
                    if "w" in version_id and len(version_id) >= 5:  # Weekly snapshots like "24w07a"
                        version_type = "snapshot"
                    elif any(keyword in version_id.lower() for keyword in ["pre", "rc", "experimental", "combat"]):
                        version_type = "snapshot"
                    else:
                        version_type = "snapshot"
                else:
                    version_type = "release"
                
                version_info = {
                    "id": version_id,
                    "type": version_type,
                    "release_time": "",
                    "stable": is_stable
                }
                all_versions.append(version_info)
            
            print(f"Loaded {len(all_versions)} Fabric-supported Minecraft versions")
            releases = sum(1 for v in all_versions if v["stable"])
            snapshots = len(all_versions) - releases
            print(f"  - {releases} releases, {snapshots} snapshots")
            print(f"  - {len(self.fabric_metadata['loader_versions'])} loader versions")
            print(f"  - {len(self.fabric_metadata['installer_versions'])} installer versions")
            
            self.all_versions["fabric"] = all_versions
            self.available_versions = [v["id"] for v in all_versions[:50]]
            # Update UI on main thread
            self.root.after(0, self.update_version_display)
            
        except Exception as e:
            print(f"Error loading fabric versions: {e}")
            # Fallback to old method if needed
            self.load_fabric_versions_fallback()
    
    def load_fabric_versions_fallback(self):
        """Fallback method using older API endpoints"""
        try:
            print("Using fallback API method for Fabric versions")
            
            # Get game versions
            game_response = requests.get("https://meta.fabricmc.net/v2/versions/game")
            game_data = game_response.json()
            
            # Get loader versions
            loader_response = requests.get("https://meta.fabricmc.net/v2/versions/loader")
            loader_data = loader_response.json()
            
            # Get installer versions
            installer_response = requests.get("https://meta.fabricmc.net/v2/versions/installer")
            installer_data = installer_response.json()
            
            # Store fabric metadata for server jar downloads
            self.fabric_metadata = {
                "loader_versions": loader_data,
                "installer_versions": installer_data
            }
            
            all_versions = []
            for v in game_data:
                # Include both stable and snapshot versions
                version_info = {
                    "id": v["version"],
                    "type": "snapshot" if not v.get("stable", True) else "release",
                    "release_time": "",
                    "stable": v.get("stable", True)
                }
                all_versions.append(version_info)
            
            self.all_versions["fabric"] = all_versions
            self.available_versions = [v["id"] for v in all_versions[:50]]
            # Update UI on main thread
            self.root.after(0, self.update_version_display)
            
        except Exception as e:
            print(f"Error in fallback fabric loading: {e}")
    
    def load_fabric_versions(self):
        """Legacy method for backward compatibility"""
        self.load_fabric_versions_bg()
    
    def update_version_display(self):
        def update():
            if self.available_versions:
                # Only set default version if no version is currently selected
                if not self.server_version.get():
                    self.server_version.set(self.available_versions[0])
                    print(f"Set default version to: {self.available_versions[0]}")  # Debug
                self.version_entry.configure(placeholder_text=self.lang.get("versions_available", len(self.available_versions)))
                # Refresh any open version selector windows
                self.refresh_version_selector()
            else:
                self.version_entry.configure(placeholder_text=self.lang.get("no_versions"))
        
        self.root.after(0, update)
    
    def refresh_version_selector(self):
        """Refresh version selector window if it's open"""
        # This will be called when versions finish loading
        # to update any open version selector windows
        pass
    
    def open_eula(self):
        webbrowser.open("https://account.mojang.com/documents/minecraft_eula")
    
    def install_server(self):
        if not self.validate_inputs():
            return
        
        self.install_button.configure(state="disabled")
        self.progress_bar.set(0)
        
        def install():
            try:
                self.update_progress(self.lang.get("creating_directory"), 0.1)
                server_dir = Path(self.server_path.get())
                server_dir.mkdir(parents=True, exist_ok=True)
                
                core = self.server_core.get().lower()
                version = self.server_version.get()
                
                if core == "vanilla":
                    self.install_vanilla_server(server_dir, version)
                elif core == "paper":
                    self.install_paper_server(server_dir, version)
                elif core == "spigot":
                    self.install_spigot_server(server_dir, version)
                elif core == "fabric":
                    self.install_fabric_server(server_dir, version)
                
                self.update_progress(self.lang.get("creating_eula"), 0.9)
                self.create_eula_file(server_dir)
                
                self.update_progress(self.lang.get("installation_completed"), 1.0)
                self.root.after(0, lambda: messagebox.showinfo(self.lang.get("success"), self.lang.get("server_installed")))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(self.lang.get("error"), self.lang.get("installation_failed", str(e))))
            finally:
                self.root.after(0, lambda: self.install_button.configure(state="normal"))
        
        threading.Thread(target=install, daemon=True).start()
    
    def validate_inputs(self):
        if not self.server_path.get():
            messagebox.showerror(self.lang.get("error"), self.lang.get("select_path_error"))
            return False
        
        if not self.server_version.get() or self.server_version.get() in [self.lang.get("loading"), self.lang.get("no_versions")]:
            messagebox.showerror(self.lang.get("error"), self.lang.get("select_version_error"))
            return False
        
        if not self.eula_accepted.get():
            messagebox.showerror(self.lang.get("error"), self.lang.get("accept_eula_error"))
            return False
        
        return True
    
    def update_progress(self, message, progress):
        self.root.after(0, lambda: self.progress_label.configure(text=message))
        self.root.after(0, lambda: self.progress_bar.set(progress))
    
    def open_settings(self):
        settings_window = ctk.CTkToplevel(self.root)
        settings_window.title(self.lang.get("settings"))
        settings_window.geometry("450x300")
        settings_window.resizable(False, False)
        
        # Make window modal
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        # Language selection
        lang_frame = ctk.CTkFrame(settings_window)
        lang_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(lang_frame, text=self.lang.get("language"), font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        languages = self.lang.get_available_languages()
        # Get current language from config, not from lang object
        current_lang = self.config.get("language", "en")
        lang_var = tk.StringVar(value=languages[current_lang])
        lang_menu = ctk.CTkOptionMenu(lang_frame, values=list(languages.values()), variable=lang_var)
        lang_menu.pack(pady=(0, 10))
        
        # Theme selection
        theme_frame = ctk.CTkFrame(settings_window)
        theme_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(theme_frame, text=self.lang.get("theme"), font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        themes = {self.lang.get("dark"): "dark", self.lang.get("light"): "light", self.lang.get("system"): "system"}
        # Get current theme from config
        current_theme = self.config.get("theme", "dark")
        theme_var = tk.StringVar(value=list(themes.keys())[list(themes.values()).index(current_theme)])
        theme_menu = ctk.CTkOptionMenu(theme_frame, values=list(themes.keys()), variable=theme_var)
        theme_menu.pack(pady=(0, 10))
        
        
        # Apply button
        def apply_settings():
            # Apply language
            selected_lang = lang_var.get()
            lang_code = next((k for k, v in languages.items() if v == selected_lang), "en")
            print(f"Changing language to: {lang_code}")  # Debug
            self.lang.set_language(lang_code)
            
            # Apply theme
            selected_theme = theme_var.get()
            theme_code = themes[selected_theme]
            print(f"Changing theme to: {theme_code}")  # Debug
            self.current_theme = theme_code
            ctk.set_appearance_mode(theme_code)
            
            # Save settings to config file
            self.config.set("language", lang_code)
            self.config.set("theme", theme_code)
            print(f"Saved to config: lang={lang_code}, theme={theme_code}")  # Debug
            
            # Update UI text for language changes
            self.update_ui_text()
            
            # Apply changes to any open project management windows
            self.refresh_project_management_ui()
            
            # Show confirmation
            messagebox.showinfo(self.lang.get("success"), self.lang.get("settings_applied_realtime"))
            
            settings_window.destroy()
        
        # Button frame for better layout
        button_frame = ctk.CTkFrame(settings_window)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        apply_button = ctk.CTkButton(button_frame, text=self.lang.get("apply_settings"), command=apply_settings, 
                                    width=200, height=40)
        apply_button.pack(pady=10)
        
        # Real-time preview functionality (language only, no theme preview)
        def on_language_change(*args):
            selected_lang = lang_var.get()
            lang_code = next((k for k, v in languages.items() if v == selected_lang), "en")
            # Update button text immediately
            temp_lang = LanguageManager(lang_code)
            apply_button.configure(text=temp_lang.get("apply_settings"))
        
        # Bind real-time language changes only
        lang_var.trace('w', on_language_change)
    
    def update_ui_text(self):
        # Update all UI text elements
        self.root.title(self.lang.get("title"))
        self.title_label.configure(text=self.lang.get("title"))
        self.settings_button.configure(text=self.lang.get("settings"))
        self.path_label.configure(text=self.lang.get("server_path"))
        self.path_entry.configure(placeholder_text=self.lang.get("select_path"))
        self.browse_button.configure(text=self.lang.get("browse"))
        self.core_label.configure(text=self.lang.get("server_core"))
        self.version_label.configure(text=self.lang.get("server_version"))
        self.version_button.configure(text=self.lang.get("select_version"))
        self.eula_title.configure(text=self.lang.get("eula_agreement"))
        self.eula_checkbox.configure(text=self.lang.get("accept_eula"))
        self.read_eula_button.configure(text=self.lang.get("read_eula"))
        self.eula_note.configure(text=self.lang.get("eula_note"))
        self.progress_label.configure(text=self.lang.get("ready_to_install"))
        self.install_button.configure(text=self.lang.get("install_server"))
        self.open_project_button.configure(text=self.lang.get("open_server_project"))
    
    def refresh_project_management_ui(self):
        """Refresh any open project management windows with new language/theme"""
        # This method allows real-time updates to project management windows
        # Currently just a placeholder for future enhancement
        pass
    
    def install_vanilla_server(self, server_dir, version):
        self.update_progress(self.lang.get("downloading", "Vanilla"), 0.3)
        
        # Get version manifest
        manifest_response = requests.get("https://piston-meta.mojang.com/mc/game/version_manifest.json")
        manifest = manifest_response.json()
        
        # Find version info
        version_info = None
        for v in manifest["versions"]:
            if v["id"] == version:
                version_info = v
                break
        
        if not version_info:
            raise Exception(f"Version {version} not found")
        
        # Get version details
        version_response = requests.get(version_info["url"])
        version_data = version_response.json()
        
        # Download server jar
        server_url = version_data["downloads"]["server"]["url"]
        server_response = requests.get(server_url)
        
        server_jar_path = server_dir / "server.jar"
        with open(server_jar_path, "wb") as f:
            f.write(server_response.content)
        
        self.update_progress(self.lang.get("creating_scripts"), 0.7)
        self.create_start_script(server_dir, "server.jar")
    
    def install_paper_server(self, server_dir, version):
        self.update_progress(self.lang.get("downloading", "Paper"), 0.3)
        
        # Get latest build for version
        builds_response = requests.get(f"https://api.papermc.io/v2/projects/paper/versions/{version}")
        builds_data = builds_response.json()
        latest_build = builds_data["builds"][-1]
        
        # Download server jar
        download_url = f"https://api.papermc.io/v2/projects/paper/versions/{version}/builds/{latest_build}/downloads/paper-{version}-{latest_build}.jar"
        server_response = requests.get(download_url)
        
        server_jar_path = server_dir / f"paper-{version}-{latest_build}.jar"
        with open(server_jar_path, "wb") as f:
            f.write(server_response.content)
        
        self.update_progress(self.lang.get("creating_scripts"), 0.7)
        self.create_start_script(server_dir, server_jar_path.name)
    
    def install_spigot_server(self, server_dir, version):
        self.update_progress(self.lang.get("downloading", "Spigot"), 0.3)
        
        # For newer versions, try automatic download from reliable sources
        success = False
        
        # Try SpigotMC Jenkins (more reliable for newer versions)
        if self.try_spigot_jenkins_download(server_dir, version):
            success = True
        
        # If automatic download fails, provide comprehensive instructions
        if not success:
            self.spigot_comprehensive_installation(server_dir, version)
    
    def try_spigot_jenkins_download(self, server_dir, version):
        """Try to download Spigot from GetBukkit.org with real download codes"""
        try:
            # First, try to get the download code from GetBukkit.org
            spigot_download_url = self.get_spigot_download_url(version)
            
            if spigot_download_url:
                print(f"Found Spigot download URL: {spigot_download_url}")
                try:
                    server_response = requests.get(spigot_download_url, timeout=60)
                    if server_response.status_code == 200 and len(server_response.content) > 1000000:  # >1MB
                        server_jar_path = server_dir / f"spigot-{version}.jar"
                        with open(server_jar_path, "wb") as f:
                            f.write(server_response.content)
                        
                        self.update_progress(self.lang.get("creating_scripts"), 0.7)
                        self.create_start_script(server_dir, server_jar_path.name)
                        
                        # Create success instructions
                        self.create_spigot_success_readme(server_dir, version)
                        return True
                except Exception as e:
                    print(f"Failed to download Spigot jar: {e}")
            
            return False
        except Exception as e:
            print(f"Error in Spigot download attempt: {e}")
            return False
    
    def get_spigot_download_url(self, version):
        """Get the actual download URL for a specific Spigot version from GetBukkit.org"""
        try:
            # 如果版本不在我們解析的列表中，先嘗試找到最接近的版本
            if hasattr(self, 'all_versions') and 'spigot' in self.all_versions:
                available_versions = [v['id'] for v in self.all_versions['spigot']]
                if version not in available_versions:
                    print(f"Version {version} not found in available versions. Available: {available_versions[:10]}...")
                    # 嘗試找到最接近的版本
                    similar_version = self.find_closest_version(version, available_versions)
                    if similar_version:
                        print(f"Using closest version: {similar_version}")
                        version = similar_version
                    else:
                        print(f"No suitable version found")
                        return None
            
            # Fetch the Spigot download page
            print(f"Fetching Spigot download page for version {version}...")
            response = requests.get("https://getbukkit.org/download/spigot", timeout=30)
            if response.status_code != 200:
                print(f"Failed to fetch page, status code: {response.status_code}")
                return None
            
            content = response.text
            import re
            
            # Method 1: Look for version number followed by download link
            # Pattern matches version number and captures the download code that follows
            pattern1 = rf'{re.escape(version)}.*?getbukkit\.org/get/([A-Za-z0-9]+)'
            match1 = re.search(pattern1, content, re.DOTALL)
            
            if match1:
                download_code = match1.group(1)
                download_url = f"https://getbukkit.org/get/{download_code}"
                print(f"Found download URL (method 1): {download_url}")
                return download_url
            
            # Method 2: Split content and look for version in chunks
            sections = content.split(version)
            if len(sections) > 1:
                # Look in the section after the version number
                after_version = sections[1][:2000]  # Look in next 2000 chars
                code_match = re.search(r'getbukkit\.org/get/([A-Za-z0-9]+)', after_version)
                if code_match:
                    download_code = code_match.group(1)
                    download_url = f"https://getbukkit.org/get/{download_code}"
                    print(f"Found download URL (method 2): {download_url}")
                    return download_url
            
            print(f"Could not find download link for Spigot {version}")
            return None
            
        except Exception as e:
            print(f"Error fetching Spigot download page: {e}")
            return None
    
    def find_closest_version(self, target_version, available_versions):
        """找到最接近的可用版本"""
        try:
            target_parts = [int(x) for x in target_version.split('.')]
            best_match = None
            best_score = float('inf')
            
            for version in available_versions:
                try:
                    version_parts = [int(x) for x in version.split('.')]
                    
                    # 計算版本距離
                    score = 0
                    for i in range(min(len(target_parts), len(version_parts))):
                        score += abs(target_parts[i] - version_parts[i]) * (1000 ** (2-i))
                    
                    if score < best_score:
                        best_score = score
                        best_match = version
                        
                except:
                    continue
            
            return best_match
        except:
            return None
    
    def create_spigot_success_readme(self, server_dir, version):
        """Create README for successful Spigot installation"""
        readme_path = server_dir / "README.txt"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"Spigot {version} Server installed successfully!\n\n")
            f.write("Starting your server:\n")
            f.write("1. Run start.bat (Windows) or start.sh (Linux/Mac)\n")
            f.write("2. Accept EULA when prompted\n")
            f.write("3. Configure server.properties as needed\n\n")
            f.write("Plugin Installation:\n")
            f.write("- Download plugins (.jar files) from SpigotMC.org\n")
            f.write("- Place them in the 'plugins' folder\n")
            f.write("- Restart the server to load plugins\n\n")
            f.write("Popular Plugin Categories:\n")
            f.write("- WorldEdit, WorldGuard (World management)\n")
            f.write("- EssentialsX (Core commands)\n")
            f.write("- Vault (Economy API)\n")
            f.write("- PlaceholderAPI (Plugin integration)\n")
    
    def spigot_comprehensive_installation(self, server_dir, version):
        """Provide comprehensive Spigot installation instructions"""
        self.update_progress(self.lang.get("spigot_note"), 0.5)
        
        # Download BuildTools automatically for user convenience
        try:
            buildtools_url = "https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar"
            response = requests.get(buildtools_url, timeout=30)
            if response.status_code == 200:
                buildtools_path = server_dir / "BuildTools.jar"
                with open(buildtools_path, "wb") as f:
                    f.write(response.content)
                buildtools_downloaded = True
            else:
                buildtools_downloaded = False
        except:
            buildtools_downloaded = False
        
        # Create comprehensive instructions
        readme_path = server_dir / "README.txt"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"Spigot {version} Installation Instructions\n")
            f.write("="*50 + "\n\n")
            
            if buildtools_downloaded:
                f.write("BuildTools.jar has been downloaded for you!\n\n")
                f.write("QUICK SETUP (Recommended):\n")
                f.write(f"1. Open command prompt in this directory\n")
                f.write(f"2. Run: java -jar BuildTools.jar --rev {version}\n")
                f.write("3. Wait for compilation to complete (5-10 minutes)\n")
                f.write("4. The spigot jar will be created automatically\n")
                f.write("5. Use the generated start scripts to run your server\n\n")
            else:
                f.write("Manual BuildTools Setup:\n")
                f.write("1. Download BuildTools.jar from:\n")
                f.write("   https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar\n")
                f.write(f"2. Place it in this directory\n")
                f.write(f"3. Run: java -jar BuildTools.jar --rev {version}\n\n")
            
            f.write("Alternative Methods:\n")
            f.write("1. Pre-built Downloads:\n")
            f.write(f"   - Try: https://getbukkit.org/download/spigot\n")
            f.write(f"   - Or: https://papermc.io/ (Paper is Spigot-compatible)\n\n")
            
            f.write("System Requirements:\n")
            f.write("- Java 17+ (for Minecraft 1.18+)\n")
            f.write("- Java 8+ (for Minecraft 1.8-1.17)\n")
            f.write("- Git (required for BuildTools)\n")
            f.write("- 2-4GB RAM available\n")
            f.write("- Windows/Linux/Mac OS\n\n")
            
            f.write("Spigot Automatic Download Support:\n")
            f.write("- Versions 1.8 through 1.21.5\n")
            f.write("- Downloads from GetBukkit.org\n")
            f.write("- No additional requirements for automatic download\n")
            f.write("- If download fails, BuildTools will be used instead\n\n")
            
            f.write("Need help? Visit:\n")
            f.write("- SpigotMC.org/wiki/spigot-installation\n")
            f.write("- SpigotMC.org/resources/ (for plugins)\n")
            f.write("- GetBukkit.org/download/spigot (manual downloads)\n")
        
        message = "Spigot installation prepared! "
        if buildtools_downloaded:
            message += "BuildTools.jar downloaded. Check README.txt for build instructions."
        else:
            message += "Check README.txt for download and build instructions."
            
        messagebox.showinfo("Spigot Installation", message)
    
    def spigot_manual_installation(self, server_dir, version):
        """Fallback method for manual Spigot installation"""
        self.update_progress(self.lang.get("spigot_note"), 0.5)
        # Create manual installation instructions
        readme_path = server_dir / "README.txt"
        with open(readme_path, "w") as f:
            f.write(f"To install Spigot {version} manually:\n\n")
            f.write("Method 1 - BuildTools (Recommended):\n")
            f.write("1. Download BuildTools.jar from https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar\n")
            f.write(f"2. Run: java -jar BuildTools.jar --rev {version}\n")
            f.write("3. The server jar will be created in this directory\n\n")
            f.write("Method 2 - GetBukkit (Alternative):\n")
            f.write(f"1. Download from https://download.getbukkit.org/spigot/spigot-{version}.jar\n")
            f.write("2. Place the jar in this directory\n")
            f.write("3. Create start scripts manually\n")
        
        messagebox.showinfo("Spigot Installation", self.lang.get("spigot_instructions", readme_path))
    
    def install_fabric_server(self, server_dir, version):
        self.update_progress(self.lang.get("downloading", "Fabric"), 0.3)
        
        try:
            # Get latest loader and installer versions
            if not hasattr(self, 'fabric_metadata'):
                # Fallback to loading metadata if not available
                self.load_fabric_versions_bg()
                if not hasattr(self, 'fabric_metadata'):
                    raise Exception("Failed to load Fabric metadata")
            
            # Get latest stable loader version
            loader_version = None
            for loader in self.fabric_metadata["loader_versions"]:
                if loader.get("stable", False):
                    loader_version = loader["version"]
                    break
            
            if not loader_version:
                loader_version = self.fabric_metadata["loader_versions"][0]["version"]
            
            # Get latest installer version
            installer_version = self.fabric_metadata["installer_versions"][0]["version"]
            
            # Download server jar directly using the API
            download_url = f"https://meta.fabricmc.net/v2/versions/loader/{version}/{loader_version}/{installer_version}/server/jar"
            
            print(f"Downloading Fabric server jar from: {download_url}")
            server_response = requests.get(download_url)
            
            if server_response.status_code == 200:
                server_jar_path = server_dir / f"fabric-server-{version}-{loader_version}.jar"
                with open(server_jar_path, "wb") as f:
                    f.write(server_response.content)
                
                self.update_progress(self.lang.get("creating_scripts"), 0.7)
                self.create_start_script(server_dir, server_jar_path.name)
                
                # Create a note about downloading mods
                readme_path = server_dir / "README.txt"
                with open(readme_path, "w") as f:
                    f.write(f"Fabric {version} Server installed successfully!\n")
                    f.write(f"Loader version: {loader_version}\n")
                    f.write(f"Installer version: {installer_version}\n\n")
                    f.write("To add mods:\n")
                    f.write("1. Create a 'mods' folder in this directory\n")
                    f.write("2. Download Fabric mods (.jar files) to the 'mods' folder\n")
                    f.write("3. Start the server using start.bat (Windows) or start.sh (Linux/Mac)\n")
                
            else:
                raise Exception(f"Failed to download Fabric server jar: HTTP {server_response.status_code}")
                
        except Exception as e:
            print(f"Error installing Fabric server: {e}")
            # Fallback to manual installation instructions
            self.update_progress(self.lang.get("fabric_note"), 0.5)
            readme_path = server_dir / "README.txt"
            with open(readme_path, "w") as f:
                f.write(f"To install Fabric {version}:\n")
                f.write("1. Download the Fabric installer from https://fabricmc.net/use/installer/\n")
                f.write("2. Run the installer and select 'Server'\n")
                f.write(f"3. Select Minecraft version {version}\n")
                f.write("4. Point the installer to this directory\n")
                f.write("5. Run the generated start script\n")
            
            messagebox.showinfo("Fabric Installation", self.lang.get("fabric_instructions", readme_path))
    
    def create_start_script(self, server_dir, jar_name):
        # Windows batch file
        bat_content = f"""@echo off
java -Xmx2G -Xms2G -jar {jar_name} nogui
pause"""
        
        with open(server_dir / "start.bat", "w") as f:
            f.write(bat_content)
        
        # Linux/Mac shell script
        sh_content = f"""#!/bin/bash
java -Xmx2G -Xms2G -jar {jar_name} nogui"""
        
        with open(server_dir / "start.sh", "w") as f:
            f.write(sh_content)
        
        # Make shell script executable on Unix systems
        try:
            os.chmod(server_dir / "start.sh", 0o755)
        except:
            pass
    
    def create_eula_file(self, server_dir):
        eula_content = """#By changing the setting below to TRUE you are indicating your agreement to our EULA (https://account.mojang.com/documents/minecraft_eula).
#Generated by Minecraft Server Installer
eula=true"""
        
        with open(server_dir / "eula.txt", "w") as f:
            f.write(eula_content)
    
    def is_version_compatible(self, core, version):
        """Check if a version is compatible with the selected server core"""
        try:
            # Parse version numbers for comparison
            def parse_version(v):
                # Handle various version formats
                v = str(v).lower()
                
                # Special snapshots and experimental versions - treat as compatible
                if any(keyword in v for keyword in ['snapshot', 'experimental', 'combat', 'pre-release', 'pre', 'rc', 'alpha', 'beta']):
                    return [99, 0, 0]  # treat special versions as very high version
                
                # Regular snapshots like "24w07a"
                if 'w' in v and len(v) >= 5:  # snapshot format like "24w07a"
                    return [99, 0, 0]  # treat snapshots as very high version
                
                # Extract numeric parts from version string
                import re
                numeric_parts = re.findall(r'\d+', v)
                if numeric_parts:
                    # Convert to integers and pad to 3 parts
                    parts = [int(p) for p in numeric_parts[:3]]
                    return parts + [0] * (3 - len(parts))
                
                # Default for unparseable versions
                return [99, 0, 0]
            
            version_parts = parse_version(version)
            
            # Define minimum versions for each core
            min_versions = {
                "fabric": [1, 14, 4],    # Fabric requires 1.14.4+
                "paper": [1, 8, 8],      # Paper minimum version
                "spigot": [1, 8, 0],     # Spigot minimum version
                "vanilla": [1, 0, 0],    # Vanilla supports all versions
            }
            
            core_lower = core.lower()
            if core_lower in min_versions:
                min_version = min_versions[core_lower]
                # Compare version arrays
                for i in range(3):
                    if version_parts[i] > min_version[i]:
                        return True
                    elif version_parts[i] < min_version[i]:
                        return False
                return True  # Equal versions are compatible
            
            return True  # Default to compatible if core not found
            
        except Exception as e:
            # Silently default to compatible on parsing errors
            return True

    def open_version_selector(self):
        if not self.available_versions:
            messagebox.showwarning("Warning", "Please wait for versions to load first.")
            return
        
        # Create version selector window
        version_window = ctk.CTkToplevel(self.root)
        version_window.title(f"{self.lang.get('select_version')} - {self.server_core.get().title()}")
        version_window.geometry("600x700")
        version_window.resizable(True, True)
        
        # Make window modal
        version_window.transient(self.root)
        version_window.grab_set()
        
        # Search frame
        search_frame = ctk.CTkFrame(version_window)
        search_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ctk.CTkLabel(search_frame, text=self.lang.get("search_versions"), font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 5))
        
        search_var = tk.StringVar()
        search_entry = ctk.CTkEntry(search_frame, textvariable=search_var, placeholder_text=self.lang.get("type_to_search"))
        search_entry.pack(fill="x", padx=10, pady=(0, 10))
        
        # Filter frame
        filter_frame = ctk.CTkFrame(version_window)
        filter_frame.pack(fill="x", padx=20, pady=(0, 10))
        
        show_all_var = tk.BooleanVar(value=False)
        show_snapshots_var = tk.BooleanVar(value=False)
        
        ctk.CTkCheckBox(filter_frame, text=self.lang.get("show_all_versions"), variable=show_all_var).pack(side="left", padx=10, pady=10)
        
        # Show snapshot checkbox for cores that support snapshots
        current_core = self.server_core.get().lower()
        if current_core in ["vanilla", "fabric"]:
            # For non-vanilla cores, default to showing snapshots
            if current_core != "vanilla":
                show_snapshots_var.set(True)
            
            ctk.CTkCheckBox(filter_frame, text=self.lang.get("include_snapshots"), variable=show_snapshots_var).pack(side="left", padx=10, pady=10)
        
        # Compatibility note
        compatibility_note = ctk.CTkLabel(filter_frame, text=self.lang.get("compatibility_note"), 
                                        font=ctk.CTkFont(size=11), text_color="gray")
        compatibility_note.pack(side="right", padx=10, pady=10)
        
        # Version list frame
        list_frame = ctk.CTkFrame(version_window)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Scrollable frame for versions
        scrollable_frame = ctk.CTkScrollableFrame(list_frame, width=460, height=400)
        scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Selected version variable
        selected_version = tk.StringVar(value=self.server_version.get())
        
        # Pagination variables
        current_page = 0
        page_size = 50
        filtered_versions_cache = []
        
        # Function to update version list with pagination
        def update_version_list():
            nonlocal current_page, filtered_versions_cache
            current_page = 0  # Reset to first page
            load_and_filter_versions()
        
        def load_and_filter_versions():
            nonlocal filtered_versions_cache
            
            # Get all versions for current server core
            all_versions = self.all_versions.get(self.server_core.get().lower(), [])
            if not all_versions:
                # Show loading message if no versions are available yet
                if not self.available_versions:
                    show_loading_screen()
                    return
                # Fallback to available_versions if all_versions is empty
                all_versions = [{"id": v, "type": "release"} for v in self.available_versions]
            
            print(f"Total versions for {self.server_core.get()}: {len(all_versions)}")
            
            # Filter versions based on search and options
            search_term = search_var.get().lower()
            filtered_versions_cache = []
            
            for version in all_versions:
                version_id = version["id"]
                version_type = version.get("type", "release")
                
                # Apply search filter
                if search_term and search_term not in version_id.lower():
                    continue
                
                # Apply type filter (only for vanilla - other cores support snapshots by default)
                current_core = self.server_core.get().lower()
                if current_core == "vanilla" and not show_snapshots_var.get() and version_type != "release":
                    continue
                
                # Apply compatibility filter
                if not self.is_version_compatible(self.server_core.get(), version_id):
                    continue
                
                filtered_versions_cache.append(version)
            
            # Apply "show all" limit
            if not show_all_var.get():
                filtered_versions_cache = filtered_versions_cache[:50]
            
            # Show first page
            show_version_page()
        
        def show_loading_screen():
            # Clear existing widgets
            for widget in scrollable_frame.winfo_children():
                widget.destroy()
                
            loading_frame = ctk.CTkFrame(scrollable_frame)
            loading_frame.pack(fill="both", expand=True, pady=50)
            
            loading_label = ctk.CTkLabel(loading_frame, text=f"{self.lang.get('loading')}...", 
                                       font=ctk.CTkFont(size=18, weight="bold"))
            loading_label.pack(pady=20)
            
            # Add a progress bar
            progress_bar = ctk.CTkProgressBar(loading_frame, width=300)
            progress_bar.pack(pady=10)
            progress_bar.set(0.5)  # Indeterminate progress
            
            loading_info = ctk.CTkLabel(loading_frame, 
                                      text=f"Loading {self.server_core.get()} versions...",
                                      font=ctk.CTkFont(size=12))
            loading_info.pack(pady=5)
        
        def show_version_page():
            # Clear existing widgets
            for widget in scrollable_frame.winfo_children():
                widget.destroy()
            
            total_versions = len(filtered_versions_cache)
            total_pages = (total_versions + page_size - 1) // page_size if total_versions > 0 else 1
            
            # Show count info and pagination info
            if total_versions > page_size:
                count_text = f"{total_versions} versions (Page {current_page + 1} of {total_pages})"
            else:
                count_text = self.lang.get("versions_available", total_versions)
            
            count_label = ctk.CTkLabel(scrollable_frame, text=count_text, font=ctk.CTkFont(size=14, weight="bold"))
            count_label.pack(pady=5)
            
            # Calculate page range
            start_idx = current_page * page_size
            end_idx = min(start_idx + page_size, total_versions)
            page_versions = filtered_versions_cache[start_idx:end_idx]
            
            # Load versions progressively to prevent UI freezing
            def load_versions_progressively(versions_to_load, index=0):
                if index >= len(versions_to_load):
                    return
                
                # Load in batches of 10 to keep UI responsive
                batch_size = 10
                end_index = min(index + batch_size, len(versions_to_load))
                
                for i in range(index, end_index):
                    version = versions_to_load[i]
                    version_id = version["id"]
                    version_type = version.get("type", "release")
                    
                    # Create frame for version item
                    version_frame = ctk.CTkFrame(scrollable_frame)
                    version_frame.pack(fill="x", pady=2)
                    
                    # Radio button for selection
                    radio = ctk.CTkRadioButton(version_frame, text="", variable=selected_version, value=version_id)
                    radio.pack(side="left", padx=10, pady=5)
                    
                    # Version info
                    version_text = version_id
                    if version_type != "release":
                        version_text += f" ({version_type})"
                    
                    # Check compatibility and add visual indicator
                    is_compatible = self.is_version_compatible(self.server_core.get(), version_id)
                    text_color = "white" if is_compatible else "gray"
                    
                    version_label = ctk.CTkLabel(version_frame, text=version_text, text_color=text_color)
                    version_label.pack(side="left", padx=(0, 10), pady=5)
                    
                    # Make the whole frame clickable
                    def on_click(vid=version_id):
                        selected_version.set(vid)
                    
                    version_frame.bind("<Button-1>", lambda e, vid=version_id: on_click(vid))
                    version_label.bind("<Button-1>", lambda e, vid=version_id: on_click(vid))
                
                # Schedule next batch
                if end_index < len(versions_to_load):
                    version_window.after(10, lambda: load_versions_progressively(versions_to_load, end_index))
            
            # Start progressive loading
            if page_versions:
                # Show loading indicator for the page
                if len(page_versions) > 20:
                    loading_indicator = ctk.CTkLabel(scrollable_frame, text="Loading versions...", 
                                                   font=ctk.CTkFont(size=12))
                    loading_indicator.pack(pady=5)
                    
                    def start_loading():
                        loading_indicator.destroy()
                        load_versions_progressively(page_versions)
                    
                    version_window.after(50, start_loading)
                else:
                    # Load immediately if small number of versions
                    load_versions_progressively(page_versions)
            
            # Add pagination controls if needed
            if total_versions > page_size:
                pagination_frame = ctk.CTkFrame(scrollable_frame)
                pagination_frame.pack(fill="x", pady=10)
                
                def prev_page():
                    nonlocal current_page
                    if current_page > 0:
                        current_page -= 1
                        show_version_page()
                
                def next_page():
                    nonlocal current_page
                    if current_page < total_pages - 1:
                        current_page += 1
                        show_version_page()
                
                # Previous button
                prev_btn = ctk.CTkButton(pagination_frame, text="← Previous", command=prev_page, 
                                       state="normal" if current_page > 0 else "disabled", width=100)
                prev_btn.pack(side="left", padx=10, pady=5)
                
                # Page info
                page_info = ctk.CTkLabel(pagination_frame, text=f"Page {current_page + 1} of {total_pages}")
                page_info.pack(side="left", expand=True, pady=5)
                
                # Next button
                next_btn = ctk.CTkButton(pagination_frame, text="Next →", command=next_page,
                                       state="normal" if current_page < total_pages - 1 else "disabled", width=100)
                next_btn.pack(side="right", padx=10, pady=5)
        
        # Bind search and filter updates
        search_var.trace('w', lambda *args: update_version_list())
        show_all_var.trace('w', lambda *args: update_version_list())
        show_snapshots_var.trace('w', lambda *args: update_version_list())
        
        # Initial population
        update_version_list()
        
        def select_version():
            if selected_version.get():
                chosen_version = selected_version.get()
                print(f"Selected version: {chosen_version}")  # Debug
                self.server_version.set(chosen_version)
                # Force update the entry field
                self.version_entry.delete(0, 'end')
                self.version_entry.insert(0, chosen_version)
                print(f"Updated server_version to: {self.server_version.get()}")  # Debug
                # Show confirmation
                messagebox.showinfo("Success", f"Version {chosen_version} selected!")
                version_window.destroy()
            else:
                print("No version selected")  # Debug
                messagebox.showwarning("Warning", "Please select a version first.")
        
        def cancel_selection():
            version_window.destroy()
        
        # Button frame - place it at the bottom
        button_frame = ctk.CTkFrame(version_window)
        button_frame.pack(fill="x", padx=20, pady=20, side="bottom")
        
        # Add buttons with clear layout
        cancel_btn = ctk.CTkButton(button_frame, text="Cancel", command=cancel_selection, width=120)
        cancel_btn.pack(side="left", padx=10, pady=10)
        
        confirm_btn = ctk.CTkButton(button_frame, text="Confirm Selection", command=select_version, 
                                   font=ctk.CTkFont(size=14, weight="bold"), width=150)
        confirm_btn.pack(side="right", padx=10, pady=10)
        
        print("Buttons created and packed")  # Debug
        
        # Focus on search entry
        search_entry.focus()
    
    def run(self):
        # Save window size on close
        def on_closing():
            try:
                # Save window size
                if hasattr(self, 'config') and self.config:
                    self.config.set("window_size", self.root.geometry())
                    
                # Close main window normally (no server warning here)
                self.root.destroy()
                    
            except Exception as e:
                print(f"Error during shutdown: {e}")
                # On error, still close
                self.root.destroy()
        
        self.root.protocol("WM_DELETE_WINDOW", on_closing)
        self.root.mainloop()

if __name__ == "__main__":
    app = MinecraftServerInstaller()
    app.run()