// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use std::process::Command;
use std::thread;

fn main() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .setup(|app| {
      println!("🚀 LISE Orchestrator Desktop starting...");
      
      // In development mode, use the executable from orchestrator/dist/
      // In production mode, use the bundled resource
      let resource_path = if cfg!(debug_assertions) {
        // Development mode - look in the orchestrator/dist directory relative to project root
        std::env::current_dir()
          .expect("failed to get current dir")
          .parent()  // Go up one level from src-tauri to project root
          .expect("failed to get parent dir")
          .join("orchestrator")
          .join("dist")
          .join("lise-orchestrator.exe")
      } else {
        // Production mode - use bundled resource
        app
          .path()
          .resource_dir()
          .expect("failed to get resource dir")
          .join("lise-orchestrator.exe")
      };
      
      thread::spawn(move || {
        println!("📡 Starting orchestrator server: {:?}", resource_path);
        
        let mut cmd = Command::new(&resource_path);
        match cmd.spawn() {
          Ok(mut child) => {
            println!("✅ Orchestrator process started with PID: {}", child.id());
            
            // Wait for the process to complete
            match child.wait() {
              Ok(status) => println!("🏁 Orchestrator process exited with status: {}", status),
              Err(e) => println!("❌ Error waiting for orchestrator process: {}", e),
            }
          }
          Err(e) => {
            println!("❌ Failed to start orchestrator: {}", e);
            println!("💡 Trying to find orchestrator at: {:?}", resource_path);
          }
        }
      });
      
      println!("🌐 Expecting Python orchestrator on http://localhost:8080");
      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
