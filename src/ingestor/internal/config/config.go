// Package config reads the mini commands' configuration from the environment,
// optionally loading a .env-style file first.
//
// The environment always wins over the file: that way a .env file serves local
// runs without getting in the way inside the container, where the variables
// already come from docker compose.
package config

import (
	"errors"
	"fmt"
	"io/fs"

	"github.com/caarlos0/env/v11"
	"github.com/joho/godotenv"
)

// Inlabs holds the INLABS credentials (free sign-up at https://inlabs.in.gov.br/).
type Inlabs struct {
	Email    string `env:"INLABS_EMAIL,required,notEmpty"`
	Password string `env:"INLABS_SENHA,required,notEmpty"`
}

// Fetch is the configuration of the fetch command.
type Fetch struct {
	Inlabs

	// OutputDir is where the downloaded zips are written. It defaults to the
	// directory the command was run from.
	OutputDir string `env:"INLABS_OUTPUT_DIR" envDefault:"."`
}

// Load fills dest — a pointer to a struct with env tags — from the
// environment, reading envFile first when one is given.
//
// An empty envFile uses the environment alone. A given envFile that does not
// exist is an error: once a path is asked for, staying quiet would hide a
// wrong working directory.
func Load(envFile string, dest any) error {
	if envFile != "" {
		if err := godotenv.Load(envFile); err != nil {
			if errors.Is(err, fs.ErrNotExist) {
				return fmt.Errorf("env file %q not found", envFile)
			}
			return fmt.Errorf("reading %q: %w", envFile, err)
		}
	}
	if err := env.Parse(dest); err != nil {
		return fmt.Errorf("invalid configuration: %w", err)
	}
	return nil
}
