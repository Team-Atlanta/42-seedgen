package main

import (
	"BugBuster/SeedD/internal/logging"
	"BugBuster/SeedD/internal/server"
	"BugBuster/SeedD/internal/utils"
	"context"
	"flag"
	"log"
	"os"
	"path/filepath"

	"go.uber.org/zap"
)

func main() {
	debug := flag.Bool("debug", false, "Enable debug logging")
	flag.Parse()

	// Initialize logger
	if err := logging.InitLogger(*debug); err != nil {
		log.Fatalf("Failed to initialize logger: %v", err)
	}
	defer logging.Sync()

	logger := logging.Logger

	// Use pre-built compilation database if available, otherwise construct it
	compilation_database_path := "/out/compile_commands"
	if _, err := os.Stat(filepath.Join(compilation_database_path, "compile_commands.json")); err != nil {
		compilation_database_path, err = utils.ConstructCompilationDatabase()
		if err != nil {
			logger.Error("Failed to construct compilation database", zap.Error(err))
		}
	}

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	logger.Info("Starting SeedD server")
	if err := server.Serve(ctx, compilation_database_path); err != nil {
		logger.Fatal("Server failed", zap.Error(err))
	}
}
