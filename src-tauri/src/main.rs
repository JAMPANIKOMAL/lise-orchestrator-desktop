// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::Manager;
use std::process::{Command, Stdio};
use std::thread;
use std::time::Duration;

fn main() {
  tauri::Builder::default()
    .setup(|app| {
      // Get the path to the sidecar executable
      let sidecar_path = app.path()
          .resource_dir()
          .expect("failed to get resource directory")
          .join("main.exe");

      println!("Starting backend at: {:?}", sidecar_path);

      // Launch the backend executable with better error handling
      match Command::new(&sidecar_path)
          .stdout(Stdio::piped())
          .stderr(Stdio::piped())
          .spawn() {
          Ok(mut child) => {
              println!("Backend process started with PID: {}", child.id());
              
              // Give the backend a moment to start
              thread::sleep(Duration::from_millis(2000));
              
              // Check if the process is still running
              match child.try_wait() {
                  Ok(Some(status)) => {
                      eprintln!("Backend process exited early with status: {}", status);
                  }
                  Ok(None) => {
                      println!("Backend process is running successfully");
                  }
                  Err(e) => {
                      eprintln!("Error checking backend process status: {}", e);
                  }
              }
          }
          Err(e) => {
              eprintln!("Failed to spawn backend: {}", e);
              return Err(Box::new(e));
          }
      }

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}