package config_test

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"conselhos-vivos/internal/config"
)

// cleanEnv removes the INLABS variables from the process and restores them at
// the end. Needed because godotenv writes to the environment: without this,
// the value loaded by one test would leak into the next. Note that unsetting
// is not the same as setting an empty value — godotenv skips any key already
// present in the environment, empty included.
func cleanEnv(t *testing.T) {
	t.Helper()
	for _, key := range []string{"INLABS_EMAIL", "INLABS_SENHA", "INLABS_OUTPUT_DIR"} {
		previous, existed := os.LookupEnv(key)
		t.Cleanup(func() {
			if existed {
				os.Setenv(key, previous)
				return
			}
			os.Unsetenv(key)
		})
		os.Unsetenv(key)
	}
}

func writeEnvFile(t *testing.T, contents string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), ".env")
	require.NoError(t, os.WriteFile(path, []byte(contents), 0o600))
	return path
}

func TestLoadFromFile(t *testing.T) {
	cleanEnv(t)
	path := writeEnvFile(t, "INLABS_EMAIL=a@b.com\nINLABS_SENHA=secret\n")

	var cfg config.Inlabs
	require.NoError(t, config.Load(path, &cfg))

	assert.Equal(t, "a@b.com", cfg.Email)
	assert.Equal(t, "secret", cfg.Password)
}

func TestEnvironmentWinsOverFile(t *testing.T) {
	cleanEnv(t)
	path := writeEnvFile(t, "INLABS_EMAIL=file@b.com\nINLABS_SENHA=from-file\n")
	t.Setenv("INLABS_EMAIL", "env@b.com")

	var cfg config.Inlabs
	require.NoError(t, config.Load(path, &cfg))

	assert.Equal(t, "env@b.com", cfg.Email, "the environment should win over the file")
	assert.Equal(t, "from-file", cfg.Password, "a key absent from the environment comes from the file")
}

func TestMissingFile(t *testing.T) {
	cleanEnv(t)

	var cfg config.Inlabs
	err := config.Load(filepath.Join(t.TempDir(), "does-not-exist"), &cfg)

	require.Error(t, err)
	assert.Contains(t, err.Error(), "does-not-exist", "the error should name the path that was not found")
}

func TestNoFileUsesEnvironmentOnly(t *testing.T) {
	cleanEnv(t)
	t.Setenv("INLABS_EMAIL", "a@b.com")
	t.Setenv("INLABS_SENHA", "secret")

	var cfg config.Inlabs
	require.NoError(t, config.Load("", &cfg))

	assert.Equal(t, "a@b.com", cfg.Email)
	assert.Equal(t, "secret", cfg.Password)
}

func TestMissingCredential(t *testing.T) {
	cleanEnv(t)
	path := writeEnvFile(t, "INLABS_EMAIL=a@b.com\n")

	var cfg config.Inlabs
	err := config.Load(path, &cfg)

	require.Error(t, err)
	assert.Contains(t, err.Error(), "INLABS_SENHA")
}

func TestFetchOutputDirDefault(t *testing.T) {
	cleanEnv(t)
	t.Setenv("INLABS_EMAIL", "a@b.com")
	t.Setenv("INLABS_SENHA", "secret")

	var cfg config.Fetch
	require.NoError(t, config.Load("", &cfg))

	assert.Equal(t, ".", cfg.OutputDir, "defaults to the directory the command was run from")
	assert.Equal(t, "a@b.com", cfg.Email, "the embedded credentials are filled too")
}

func TestFetchOutputDirFromFile(t *testing.T) {
	cleanEnv(t)
	path := writeEnvFile(t, "INLABS_EMAIL=a@b.com\nINLABS_SENHA=secret\nINLABS_OUTPUT_DIR=/tmp/zips\n")

	var cfg config.Fetch
	require.NoError(t, config.Load(path, &cfg))

	assert.Equal(t, "/tmp/zips", cfg.OutputDir)
}
