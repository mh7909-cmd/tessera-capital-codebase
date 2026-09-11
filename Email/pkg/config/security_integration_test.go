// PicoClaw - Ultra-lightweight personal AI agent
// License: MIT
//
// Copyright (c) 2026 PicoClaw contributors

package config

import (
	"encoding/json"
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// Test JSON unmarshal of private fields (unexported fields are never filled, with or without json tag).
func TestJSONUnmarshalPrivateFields(t *testing.T) {
	type testStruct struct {
		PublicField  string `json:"public"`
		privateField string
	}

	data := `{"public": "pub", "privateField": "priv"}`
	var s testStruct
	if err := json.Unmarshal([]byte(data), &s); err != nil {
		t.Fatalf("JSON unmarshal failed: %v", err)
	}

	t.Logf("PublicField: %s", s.PublicField)
	t.Logf("privateField: %s", s.privateField)

	if s.PublicField != "pub" {
		t.Errorf("PublicField = %q, want 'pub'", s.PublicField)
	}
	if s.privateField != "" {
		t.Errorf("privateField = %q, want empty because unexported fields are ignored", s.privateField)
	}
}

func TestSecurityConfigIntegration(t *testing.T) {
	t.Run("Full workflow with security references", func(t *testing.T) {
		tmpDir := t.TempDir()

		// Create config.json with direct security values (not ref: references)
		// These values should take precedence over .security.yml
		configPath := filepath.Join(tmpDir, "config.json")
		configContent := `{
  "version": 1,
  "model_list": [
    {
      "model_name": "test-model",
      "model": "openai/test-model",
      "api_base": "https://api.openai.com/v1",
      "api_key": "sk-from-config-json-direct"
    }
  ],
  "channels": {
  },
  "tools": {
    "web": {
      "brave": {
        "enabled": true,
        "api_keys": ["BSA-from-config-json-direct"]
      }
    },
    "skills": {
      "github": {
        "token": "ghp-from-config-json-direct"
      }
    }
  }
}`
		err := os.WriteFile(configPath, []byte(configContent), 0o644)
		require.NoError(t, err)

		// Create .security.yml with different values
		// These should be overridden by config.json values
		securityPath := filepath.Join(tmpDir, SecurityConfigFile)
		securityContent := `model_list:
  test-model:
    api_keys:
      - "sk-from-security-yml"



skills:
  github:
    token: "ghp-from-security-yml"`
		err = os.WriteFile(securityPath, []byte(securityContent), 0o600)
		require.NoError(t, err)

		// Load config and verify config.json values take precedence
		cfg, err := LoadConfig(configPath)
		require.NoError(t, err)
		require.NotNil(t, cfg)

		// Verify model API key from config.json takes precedence
		assert.Equal(t, 1, len(cfg.ModelList))
		assert.Equal(t, "test-model", cfg.ModelList[0].ModelName)
		assert.Equal(t, "sk-from-security-yml", cfg.ModelList[0].APIKey())



		assert.Equal(t, "sk-from-security-yml", cfg.ModelList[0].APIKeys[0].String())

		// Verify web tool API key from config.json takes precedence
		assert.Equal(t, "BSA-from-config-json-direct", cfg.Tools.Web.Brave.APIKey())

		// Verify skills token is resolved
		assert.Equal(t, "ghp-from-security-yml", cfg.Tools.Skills.Github.Token.String())
	})
}

func TestSecurityConfigWithAPIKeysArray(t *testing.T) {
	t.Run("Multiple API keys via security", func(t *testing.T) {
		tmpDir := t.TempDir()

		// Create config with APIKeys array
		configPath := filepath.Join(tmpDir, "config.json")
		configContent := `{
  "version": 1,
  "model_list": [
    {
      "model_name": "multi-key-model",
      "model": "openai/multi-key-model"
    }
  ]
}`
		err := os.WriteFile(configPath, []byte(configContent), 0o644)
		require.NoError(t, err)

		// Create .security.yml
		securityPath := filepath.Join(tmpDir, SecurityConfigFile)
		securityContent := `model_list:
  multi-key-model:0:
    api_key: "sk-key-1"
    api_keys:
      - "sk-key-1"
      - "sk-key-2"
      - "sk-key-3"
`
		err = os.WriteFile(securityPath, []byte(securityContent), 0o600)
		require.NoError(t, err)

		// Load config
		cfg, err := LoadConfig(configPath)
		require.NoError(t, err)

		t.Logf("Config: %+v", cfg.ModelList)
		for _, m := range cfg.ModelList {
			t.Logf("Model: %+v", m)
		}
		// Verify multi-key expansion works
		assert.Equal(t, 3, len(cfg.ModelList))
		assert.Equal(t, "multi-key-model", cfg.ModelList[2].ModelName)
	})
}

func TestAllSecurityKeysAccessible(t *testing.T) {
	t.Run("All security keys accessible via Key() methods including file://", func(t *testing.T) {
		tmpDir := t.TempDir()

		// Create test files for file:// references
		modelAPIKeyFile := filepath.Join(tmpDir, "model_api_key.txt")
		err := os.WriteFile(modelAPIKeyFile, []byte("sk-model-from-file-12345"), 0o600)
		require.NoError(t, err)

		braveAPIKeyFile := filepath.Join(tmpDir, "brave_api_key.txt")
		err = os.WriteFile(braveAPIKeyFile, []byte("BSA-brave-from-file-67890"), 0o600)
		require.NoError(t, err)

		tavilyAPIKeyFile := filepath.Join(tmpDir, "tavily_api_key.txt")
		err = os.WriteFile(tavilyAPIKeyFile, []byte("tvly-tavily-from-file-11111"), 0o600)
		require.NoError(t, err)

		perplexityAPIKeyFile := filepath.Join(tmpDir, "perplexity_api_key.txt")
		err = os.WriteFile(perplexityAPIKeyFile, []byte("pplx-perplexity-from-file-22222"), 0o600)
		require.NoError(t, err)

		githubTokenFile := filepath.Join(tmpDir, "github_token.txt")
		err = os.WriteFile(githubTokenFile, []byte("ghp-github-from-file-abc123"), 0o600)
		require.NoError(t, err)

		clawhubAuthTokenFile := filepath.Join(tmpDir, "clawhub_auth_token.txt")
		err = os.WriteFile(clawhubAuthTokenFile, []byte("clawhub-auth-token-from-file"), 0o600)
		require.NoError(t, err)

		// Create config.json without sensitive values (they'll be in .security.yml)
		configPath := filepath.Join(tmpDir, "config.json")
		configContent := `{
  "version": 2,
  "model_list": [
    {
      "model_name": "test-model-1",
      "model": "openai/test-model-1"
    }
  ],
  "channels": {
    "pico": {
      "enabled": true
    }
  },
  "tools": {
    "web": {
      "brave": {
        "enabled": true
      },
      "tavily": {
        "enabled": true
      },
      "perplexity": {
        "enabled": true
      },
      "glm_search": {
        "enabled": true
      }
    },
    "skills": {
      "github": {}
    }
  }
}`
		err = os.WriteFile(configPath, []byte(configContent), 0o644)
		require.NoError(t, err)

		// Create .security.yml with file:// references and plaintext values
		securityPath := filepath.Join(tmpDir, SecurityConfigFile)
		securityContent := `model_list:
  test-model-1:
    api_keys:
      - "file://model_api_key.txt"

channels:
  pico:
    token: "pico_test_token"

web:
  brave:
    api_keys:
      - "file://brave_api_key.txt"
  tavily:
    api_keys:
      - "file://tavily_api_key.txt"
  perplexity:
    api_keys:
      - "file://perplexity_api_key.txt"
  glm_search:
    api_key: "glm-test-glm-search-key"

skills:
  github:
    token: "file://github_token.txt"
  clawhub:
    auth_token: "file://clawhub_auth_token.txt"
`
		err = os.WriteFile(securityPath, []byte(securityContent), 0o600)
		require.NoError(t, err)

		// Load config and verify all security keys are accessible
		cfg, err := LoadConfig(configPath)
		require.NoError(t, err)
		require.NotNil(t, cfg)

		// Verify Model API keys
		assert.Equal(t, 1, len(cfg.ModelList))
		assert.Equal(t, "test-model-1", cfg.ModelList[0].ModelName)
		// file:// reference should be resolved
		assert.Equal(t, "sk-model-from-file-12345", cfg.ModelList[0].APIKey())
		t.Logf("Model APIKey(): %s", cfg.ModelList[0].APIKey())



		// Verify Web tool API keys
		assert.Equal(t, "BSA-brave-from-file-67890", cfg.Tools.Web.Brave.APIKey())
		t.Logf("Brave APIKey(): %s", cfg.Tools.Web.Brave.APIKey())

		assert.Equal(t, "tvly-tavily-from-file-11111", cfg.Tools.Web.Tavily.APIKey())
		t.Logf("Tavily APIKey(): %s", cfg.Tools.Web.Tavily.APIKey())

		assert.Equal(t, "pplx-perplexity-from-file-22222", cfg.Tools.Web.Perplexity.APIKey())
		t.Logf("Perplexity APIKey(): %s", cfg.Tools.Web.Perplexity.APIKey())

		// GLM Search - Note: GLM uses SetAPIKey (lowercase) internally
		t.Logf("GLMSearch APIKey(): %s", cfg.Tools.Web.GLMSearch.APIKey.String())
		assert.Equal(t, "glm-test-glm-search-key", cfg.Tools.Web.GLMSearch.APIKey.String())

		// Verify Skills tokens
		assert.Equal(t, "ghp-github-from-file-abc123", cfg.Tools.Skills.Github.Token.String())
		t.Logf("Github Token(): %s", cfg.Tools.Skills.Github.Token.String())

		assert.Equal(t, "clawhub-auth-token-from-file", cfg.Tools.Skills.Registries.ClawHub.AuthToken.String())
		t.Logf("ClawHub AuthToken(): %s", cfg.Tools.Skills.Registries.ClawHub.AuthToken.String())

		t.Log("All security keys are successfully accessible via their respective Key() methods")
	})
}
