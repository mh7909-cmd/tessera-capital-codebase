// PicoClaw - Ultra-lightweight personal AI agent
// License: MIT
//
// Copyright (c) 2026 PicoClaw contributors

package config

import (
	"encoding/json"
)

type agentDefaultsV0 struct {
	Workspace                 string         `json:"workspace"                       env:"PICOCLAW_AGENTS_DEFAULTS_WORKSPACE"`
	RestrictToWorkspace       bool           `json:"restrict_to_workspace"           env:"PICOCLAW_AGENTS_DEFAULTS_RESTRICT_TO_WORKSPACE"`
	AllowReadOutsideWorkspace bool           `json:"allow_read_outside_workspace"    env:"PICOCLAW_AGENTS_DEFAULTS_ALLOW_READ_OUTSIDE_WORKSPACE"`
	Provider                  string         `json:"provider"                        env:"PICOCLAW_AGENTS_DEFAULTS_PROVIDER"`
	ModelName                 string         `json:"model_name,omitempty"            env:"PICOCLAW_AGENTS_DEFAULTS_MODEL_NAME"`
	Model                     string         `json:"model"                           env:"PICOCLAW_AGENTS_DEFAULTS_MODEL"` // Deprecated: use model_name instead
	ModelFallbacks            []string       `json:"model_fallbacks,omitempty"`
	ImageModel                string         `json:"image_model,omitempty"           env:"PICOCLAW_AGENTS_DEFAULTS_IMAGE_MODEL"`
	ImageModelFallbacks       []string       `json:"image_model_fallbacks,omitempty"`
	MaxTokens                 int            `json:"max_tokens"                      env:"PICOCLAW_AGENTS_DEFAULTS_MAX_TOKENS"`
	Temperature               *float64       `json:"temperature,omitempty"           env:"PICOCLAW_AGENTS_DEFAULTS_TEMPERATURE"`
	MaxToolIterations         int            `json:"max_tool_iterations"             env:"PICOCLAW_AGENTS_DEFAULTS_MAX_TOOL_ITERATIONS"`
	SummarizeMessageThreshold int            `json:"summarize_message_threshold"     env:"PICOCLAW_AGENTS_DEFAULTS_SUMMARIZE_MESSAGE_THRESHOLD"`
	SummarizeTokenPercent     int            `json:"summarize_token_percent"         env:"PICOCLAW_AGENTS_DEFAULTS_SUMMARIZE_TOKEN_PERCENT"`
	MaxMediaSize              int            `json:"max_media_size,omitempty"        env:"PICOCLAW_AGENTS_DEFAULTS_MAX_MEDIA_SIZE"`
	Routing                   *RoutingConfig `json:"routing,omitempty"`
}

// GetModelName returns the effective model name for the agent defaults.
// It prefers the new "model_name" field but falls back to "model" for backward compatibility.
func (d *agentDefaultsV0) GetModelName() string {
	if d.ModelName != "" {
		return d.ModelName
	}
	return d.Model
}

type agentsConfigV0 struct {
	Defaults agentDefaultsV0 `json:"defaults"`
	List     []AgentConfig   `json:"list,omitempty"`
}

// configV0 represents the config structure before versioning was introduced.
// This struct is used for loading legacy config files (version 0).
// It is unexported since it's only used internally for migration.
type configV0 struct {
	Agents    agentsConfigV0    `json:"agents"`
	Bindings  []AgentBinding    `json:"bindings,omitempty"`
	Session   SessionConfig     `json:"session,omitempty"`
	Channels  channelsConfigV0  `json:"channels"`
	Providers providersConfigV0 `json:"providers,omitempty"`
	ModelList []modelConfigV0   `json:"model_list"`
	Gateway   GatewayConfig     `json:"gateway"`
	Tools     toolsConfigV0     `json:"tools"`
	Heartbeat HeartbeatConfig   `json:"heartbeat"`
}

type toolsConfigV0 struct {
	AllowReadPaths  []string            `json:"allow_read_paths"  env:"PICOCLAW_TOOLS_ALLOW_READ_PATHS"`
	AllowWritePaths []string            `json:"allow_write_paths" env:"PICOCLAW_TOOLS_ALLOW_WRITE_PATHS"`
	Web             webToolsConfigV0    `json:"web"`
	Cron            CronToolsConfig     `json:"cron"`
	Exec            ExecConfig          `json:"exec"`
	Skills          skillsToolsConfigV0 `json:"skills"`
	MediaCleanup    MediaCleanupConfig  `json:"media_cleanup"`
	MCP             MCPConfig           `json:"mcp"`
	AppendFile      ToolConfig          `json:"append_file"                                              envPrefix:"PICOCLAW_TOOLS_APPEND_FILE_"`
	EditFile        ToolConfig          `json:"edit_file"                                                envPrefix:"PICOCLAW_TOOLS_EDIT_FILE_"`
	FindSkills      ToolConfig          `json:"find_skills"                                              envPrefix:"PICOCLAW_TOOLS_FIND_SKILLS_"`
	ReadFile        ReadFileToolConfig  `json:"read_file"                                                envPrefix:"PICOCLAW_TOOLS_READ_FILE_"`
	SendFile        ToolConfig          `json:"send_file"                                                envPrefix:"PICOCLAW_TOOLS_SEND_FILE_"`
	Spawn           ToolConfig          `json:"spawn"                                                    envPrefix:"PICOCLAW_TOOLS_SPAWN_"`
	SpawnStatus     ToolConfig          `json:"spawn_status"                                             envPrefix:"PICOCLAW_TOOLS_SPAWN_STATUS_"`
	Subagent        ToolConfig          `json:"subagent"                                                 envPrefix:"PICOCLAW_TOOLS_SUBAGENT_"`
	WebFetch        ToolConfig          `json:"web_fetch"                                                envPrefix:"PICOCLAW_TOOLS_WEB_FETCH_"`
	WriteFile       ToolConfig          `json:"write_file"                                               envPrefix:"PICOCLAW_TOOLS_WRITE_FILE_"`
}

type channelsConfigV0 struct {
	Pico     picoConfigV0     `json:"pico"`
}

func (v *channelsConfigV0) ToChannelsConfig() ChannelsConfig {
	pico := v.Pico.ToPicoConfig()

	return ChannelsConfig{
		Pico:     pico,
	}
}



type picoConfigV0 struct {
	Enabled         bool                `json:"enabled"                     env:"PICOCLAW_CHANNELS_PICO_ENABLED"`
	Token           string              `json:"token"                       env:"PICOCLAW_CHANNELS_PICO_TOKEN"`
	AllowTokenQuery bool                `json:"allow_token_query,omitempty"`
	AllowOrigins    []string            `json:"allow_origins,omitempty"`
	PingInterval    int                 `json:"ping_interval,omitempty"`
	ReadTimeout     int                 `json:"read_timeout,omitempty"`
	WriteTimeout    int                 `json:"write_timeout,omitempty"`
	MaxConnections  int                 `json:"max_connections,omitempty"`
	AllowFrom       FlexibleStringSlice `json:"allow_from"                  env:"PICOCLAW_CHANNELS_PICO_ALLOW_FROM"`
	Placeholder     PlaceholderConfig   `json:"placeholder,omitempty"`
}

func (v *picoConfigV0) ToPicoConfig() PicoConfig {
	cfg := PicoConfig{
		Enabled:         v.Enabled,
		AllowTokenQuery: v.AllowTokenQuery,
		AllowOrigins:    v.AllowOrigins,
		PingInterval:    v.PingInterval,
		ReadTimeout:     v.ReadTimeout,
		WriteTimeout:    v.WriteTimeout,
		MaxConnections:  v.MaxConnections,
		AllowFrom:       v.AllowFrom,
		Placeholder:     v.Placeholder,
	}
	if v.Token != "" {
		cfg.Token = *NewSecureString(v.Token)
	}
	return cfg
}



type providersConfigV0 struct {
	Anthropic     providerConfigV0       `json:"anthropic"`
	OpenAI        openAIProviderConfigV0 `json:"openai"`
	LiteLLM       providerConfigV0       `json:"litellm"`
	OpenRouter    providerConfigV0       `json:"openrouter"`
	Groq          providerConfigV0       `json:"groq"`
	Zhipu         providerConfigV0       `json:"zhipu"`
	VLLM          providerConfigV0       `json:"vllm"`
	Gemini        providerConfigV0       `json:"gemini"`
	Nvidia        providerConfigV0       `json:"nvidia"`
	Ollama        providerConfigV0       `json:"ollama"`
	Moonshot      providerConfigV0       `json:"moonshot"`
	ShengSuanYun  providerConfigV0       `json:"shengsuanyun"`
	DeepSeek      providerConfigV0       `json:"deepseek"`
	Cerebras      providerConfigV0       `json:"cerebras"`
	Vivgrid       providerConfigV0       `json:"vivgrid"`
	VolcEngine    providerConfigV0       `json:"volcengine"`
	GitHubCopilot providerConfigV0       `json:"github_copilot"`
	Antigravity   providerConfigV0       `json:"antigravity"`
	Qwen          providerConfigV0       `json:"qwen"`
	Mistral       providerConfigV0       `json:"mistral"`
	Avian         providerConfigV0       `json:"avian"`
	Minimax       providerConfigV0       `json:"minimax"`
	LongCat       providerConfigV0       `json:"longcat"`
	ModelScope    providerConfigV0       `json:"modelscope"`
	Novita        providerConfigV0       `json:"novita"`
}

// IsEmpty checks if all provider configs are empty (no API keys or API bases set)
// Note: WebSearch is an optimization option and doesn't count as "non-empty"
func (p providersConfigV0) IsEmpty() bool {
	return p.Anthropic.APIKey == "" && p.Anthropic.APIBase == "" &&
		p.OpenAI.APIKey == "" && p.OpenAI.APIBase == "" &&
		p.LiteLLM.APIKey == "" && p.LiteLLM.APIBase == "" &&
		p.OpenRouter.APIKey == "" && p.OpenRouter.APIBase == "" &&
		p.Groq.APIKey == "" && p.Groq.APIBase == "" &&
		p.Zhipu.APIKey == "" && p.Zhipu.APIBase == "" &&
		p.VLLM.APIKey == "" && p.VLLM.APIBase == "" &&
		p.Gemini.APIKey == "" && p.Gemini.APIBase == "" &&
		p.Nvidia.APIKey == "" && p.Nvidia.APIBase == "" &&
		p.Ollama.APIKey == "" && p.Ollama.APIBase == "" &&
		p.Moonshot.APIKey == "" && p.Moonshot.APIBase == "" &&
		p.ShengSuanYun.APIKey == "" && p.ShengSuanYun.APIBase == "" &&
		p.DeepSeek.APIKey == "" && p.DeepSeek.APIBase == "" &&
		p.Cerebras.APIKey == "" && p.Cerebras.APIBase == "" &&
		p.Vivgrid.APIKey == "" && p.Vivgrid.APIBase == "" &&
		p.VolcEngine.APIKey == "" && p.VolcEngine.APIBase == "" &&
		p.GitHubCopilot.APIKey == "" && p.GitHubCopilot.APIBase == "" &&
		p.Antigravity.APIKey == "" && p.Antigravity.APIBase == "" &&
		p.Qwen.APIKey == "" && p.Qwen.APIBase == "" &&
		p.Mistral.APIKey == "" && p.Mistral.APIBase == "" &&
		p.Avian.APIKey == "" && p.Avian.APIBase == "" &&
		p.Minimax.APIKey == "" && p.Minimax.APIBase == "" &&
		p.LongCat.APIKey == "" && p.LongCat.APIBase == "" &&
		p.ModelScope.APIKey == "" && p.ModelScope.APIBase == "" &&
		p.Novita.APIKey == "" && p.Novita.APIBase == ""
}

type providerConfigV0 struct {
	APIKey         string `json:"api_key"                   env:"PICOCLAW_PROVIDERS_{{.Name}}_API_KEY"`
	APIBase        string `json:"api_base"                  env:"PICOCLAW_PROVIDERS_{{.Name}}_API_BASE"`
	Proxy          string `json:"proxy,omitempty"           env:"PICOCLAW_PROVIDERS_{{.Name}}_PROXY"`
	RequestTimeout int    `json:"request_timeout,omitempty" env:"PICOCLAW_PROVIDERS_{{.Name}}_REQUEST_TIMEOUT"`
	AuthMethod     string `json:"auth_method,omitempty"     env:"PICOCLAW_PROVIDERS_{{.Name}}_AUTH_METHOD"`
	ConnectMode    string `json:"connect_mode,omitempty"    env:"PICOCLAW_PROVIDERS_{{.Name}}_CONNECT_MODE"` // only for Github Copilot, `stdio` or `grpc`
}

// MarshalJSON implements custom JSON marshaling for providersConfig
// to omit the entire section when empty
func (p providersConfigV0) MarshalJSON() ([]byte, error) {
	if p.IsEmpty() {
		return []byte("null"), nil
	}
	type Alias providersConfigV0
	return json.Marshal((*Alias)(&p))
}

type openAIProviderConfigV0 struct {
	providerConfigV0
	WebSearch bool `json:"web_search" env:"PICOCLAW_PROVIDERS_OPENAI_WEB_SEARCH"`
}

type modelConfigV0 struct {
	// Required fields
	ModelName string `json:"model_name"` // User-facing alias for the model
	Model     string `json:"model"`      // Protocol/model-identifier (e.g., "openai/gpt-4o", "anthropic/claude-sonnet-4.6")

	// HTTP-based providers
	APIBase   string   `json:"api_base,omitempty"`  // API endpoint URL
	APIKey    string   `json:"api_key"`             // API authentication key (single key)
	APIKeys   []string `json:"api_keys,omitempty"`  // API authentication keys (multiple keys for failover)
	Proxy     string   `json:"proxy,omitempty"`     // HTTP proxy URL
	Fallbacks []string `json:"fallbacks,omitempty"` // Fallback model names for failover

	// Special providers (CLI-based, OAuth, etc.)
	AuthMethod  string `json:"auth_method,omitempty"`  // Authentication method: oauth, token
	ConnectMode string `json:"connect_mode,omitempty"` // Connection mode: stdio, grpc
	Workspace   string `json:"workspace,omitempty"`    // Workspace path for CLI-based providers

	// Optional optimizations
	RPM            int    `json:"rpm,omitempty"`              // Requests per minute limit
	MaxTokensField string `json:"max_tokens_field,omitempty"` // Field name for max tokens (e.g., "max_completion_tokens")
	RequestTimeout int    `json:"request_timeout,omitempty"`
	ThinkingLevel  string `json:"thinking_level,omitempty"` // Extended thinking: off|low|medium|high|xhigh|adaptive
}

func (c *configV0) migrateChannelConfigs() {
}


func (c *configV0) Migrate() (*Config, error) {
	// Migrate legacy channel config fields to new unified structures
	cfg := DefaultConfig()

	// Always copy user's Agents config to preserve settings like Provider, Model, MaxTokens
	cfg.Agents.List = c.Agents.List
	cfg.Agents.Defaults.Workspace = c.Agents.Defaults.Workspace
	cfg.Agents.Defaults.RestrictToWorkspace = c.Agents.Defaults.RestrictToWorkspace
	cfg.Agents.Defaults.AllowReadOutsideWorkspace = c.Agents.Defaults.AllowReadOutsideWorkspace
	cfg.Agents.Defaults.Provider = c.Agents.Defaults.Provider
	cfg.Agents.Defaults.ModelName = c.Agents.Defaults.GetModelName()
	cfg.Agents.Defaults.ModelFallbacks = c.Agents.Defaults.ModelFallbacks
	cfg.Agents.Defaults.ImageModel = c.Agents.Defaults.ImageModel
	cfg.Agents.Defaults.ImageModelFallbacks = c.Agents.Defaults.ImageModelFallbacks
	cfg.Agents.Defaults.MaxTokens = c.Agents.Defaults.MaxTokens
	cfg.Agents.Defaults.Temperature = c.Agents.Defaults.Temperature
	cfg.Agents.Defaults.MaxToolIterations = c.Agents.Defaults.MaxToolIterations
	cfg.Agents.Defaults.SummarizeMessageThreshold = c.Agents.Defaults.SummarizeMessageThreshold
	cfg.Agents.Defaults.SummarizeTokenPercent = c.Agents.Defaults.SummarizeTokenPercent
	cfg.Agents.Defaults.MaxMediaSize = c.Agents.Defaults.MaxMediaSize
	cfg.Agents.Defaults.Routing = c.Agents.Defaults.Routing

	// Copy other top-level fields
	cfg.Bindings = c.Bindings
	cfg.Session = c.Session
	cfg.Channels = c.Channels.ToChannelsConfig()
	cfg.Gateway = c.Gateway
	cfg.Tools.Web = c.Tools.Web.ToWebToolsConfig()
	cfg.Tools.Cron = c.Tools.Cron
	cfg.Tools.Exec = c.Tools.Exec
	cfg.Tools.Skills = c.Tools.Skills.ToSkillsToolsConfig()
	cfg.Tools.MediaCleanup = c.Tools.MediaCleanup
	cfg.Tools.MCP = c.Tools.MCP
	cfg.Tools.AppendFile = c.Tools.AppendFile
	cfg.Tools.EditFile = c.Tools.EditFile
	cfg.Tools.FindSkills = c.Tools.FindSkills
	cfg.Tools.AllowReadPaths = c.Tools.AllowReadPaths
	cfg.Tools.AllowWritePaths = c.Tools.AllowWritePaths
	cfg.Heartbeat = c.Heartbeat

	if len(c.ModelList) > 0 {
		// Convert []modelConfigV0 to []ModelConfig
		cfg.ModelList = make([]*ModelConfig, len(c.ModelList))
		for i, m := range c.ModelList {
			mergedKeys := toSecureStrings(mergeAPIKeys(m.APIKey, m.APIKeys))
			mc := &ModelConfig{
				ModelName:      m.ModelName,
				Model:          m.Model,
				APIBase:        m.APIBase,
				Proxy:          m.Proxy,
				Fallbacks:      m.Fallbacks,
				AuthMethod:     m.AuthMethod,
				ConnectMode:    m.ConnectMode,
				Workspace:      m.Workspace,
				RPM:            m.RPM,
				MaxTokensField: m.MaxTokensField,
				RequestTimeout: m.RequestTimeout,
				ThinkingLevel:  m.ThinkingLevel,
				APIKeys:        mergedKeys,
			}
			// Infer Enabled during V0→V1 migration
			if len(mergedKeys) > 0 || m.ModelName == "local-model" {
				mc.Enabled = true
			}
			cfg.ModelList[i] = mc
		}
	}

	cfg.Version = CurrentVersion
	return cfg, nil
}

type configV1 struct {
	Config
}

// Migrate applies V1→Current Version migrations to an already-loaded Config.
//
// It must be called AFTER loadSecurityConfig so that API keys (which live in
// the security file) are available for the Enabled inference.
func (c *configV1) Migrate() (*Config, error) {
	c.migrateModelEnabled()
	c.migrateChannelConfigs()
	return &c.Config, nil
}

// migrateModelEnabled infers the Enabled field for models loaded from V1 configs
// that predate the field (JSON where "enabled" is absent).
//
// Rules (only applied when Enabled has not been explicitly set by the user):
//   - Models with API keys are considered enabled.
//   - The reserved "local-model" entry is considered enabled.
func (cfg *configV1) migrateModelEnabled() {
	for _, m := range cfg.ModelList {
		if m.Enabled {
			continue
		}
		if len(m.APIKeys) > 0 || m.ModelName == "local-model" {
			m.Enabled = true
		}
	}
}

func (cfg *configV1) migrateChannelConfigs() {
}

type webToolsConfigV0 struct {
	ToolConfig           `                    envPrefix:"PICOCLAW_TOOLS_WEB_"`
	Brave                braveConfigV0       `                                json:"brave"`
	Tavily               tavilyConfigV0      `                                json:"tavily"`
	DuckDuckGo           DuckDuckGoConfig    `                                json:"duckduckgo"`
	Perplexity           perplexityConfigV0  `                                json:"perplexity"`
	SearXNG              SearXNGConfig       `                                json:"searxng"`
	GLMSearch            glmSearchConfigV0   `                                json:"glm_search"`
	BaiduSearch          baiduSearchConfigV0 `                                json:"baidu_search"`
	PreferNative         bool                `                                json:"prefer_native"                    env:"PICOCLAW_TOOLS_WEB_PREFER_NATIVE"`
	Proxy                string              `                                json:"proxy,omitempty"                  env:"PICOCLAW_TOOLS_WEB_PROXY"`
	FetchLimitBytes      int64               `                                json:"fetch_limit_bytes,omitempty"      env:"PICOCLAW_TOOLS_WEB_FETCH_LIMIT_BYTES"`
	Format               string              `                                json:"format,omitempty"                 env:"PICOCLAW_TOOLS_WEB_FORMAT"`
	PrivateHostWhitelist FlexibleStringSlice `                                json:"private_host_whitelist,omitempty" env:"PICOCLAW_TOOLS_WEB_PRIVATE_HOST_WHITELIST"`
}

type braveConfigV0 struct {
	Enabled    bool     `json:"enabled"     env:"PICOCLAW_TOOLS_WEB_BRAVE_ENABLED"`
	APIKey     string   `json:"api_key"     env:"PICOCLAW_TOOLS_WEB_BRAVE_API_KEY"`
	APIKeys    []string `json:"api_keys"    env:"PICOCLAW_TOOLS_WEB_BRAVE_API_KEYS"`
	MaxResults int      `json:"max_results" env:"PICOCLAW_TOOLS_WEB_BRAVE_MAX_RESULTS"`
}

func toSecureStrings(keys []string) SecureStrings {
	apikeys := make(SecureStrings, len(keys))
	for i, key := range keys {
		apikeys[i] = NewSecureString(key)
	}
	return apikeys
}

func (v *braveConfigV0) ToBraveConfig() BraveConfig {
	return BraveConfig{
		Enabled:    v.Enabled,
		MaxResults: v.MaxResults,
		APIKeys:    toSecureStrings(mergeAPIKeys(v.APIKey, v.APIKeys)),
	}
}

type tavilyConfigV0 struct {
	Enabled    bool     `json:"enabled"     env:"PICOCLAW_TOOLS_WEB_TAVILY_ENABLED"`
	APIKey     string   `json:"api_key"     env:"PICOCLAW_TOOLS_WEB_TAVILY_API_KEY"`
	APIKeys    []string `json:"api_keys"    env:"PICOCLAW_TOOLS_WEB_TAVILY_API_KEYS"`
	BaseURL    string   `json:"base_url"    env:"PICOCLAW_TOOLS_WEB_TAVILY_BASE_URL"`
	MaxResults int      `json:"max_results" env:"PICOCLAW_TOOLS_WEB_TAVILY_MAX_RESULTS"`
}

func (v *tavilyConfigV0) ToTavilyConfig() TavilyConfig {
	return TavilyConfig{
		Enabled:    v.Enabled,
		BaseURL:    v.BaseURL,
		MaxResults: v.MaxResults,
		APIKeys:    toSecureStrings(mergeAPIKeys(v.APIKey, v.APIKeys)),
	}
}

type perplexityConfigV0 struct {
	Enabled    bool     `json:"enabled"     env:"PICOCLAW_TOOLS_WEB_PERPLEXITY_ENABLED"`
	APIKey     string   `json:"api_key"     env:"PICOCLAW_TOOLS_WEB_PERPLEXITY_API_KEY"`
	APIKeys    []string `json:"api_keys"    env:"PICOCLAW_TOOLS_WEB_PERPLEXITY_API_KEYS"`
	MaxResults int      `json:"max_results" env:"PICOCLAW_TOOLS_WEB_PERPLEXITY_MAX_RESULTS"`
}

func (v *perplexityConfigV0) ToPerplexityConfig() PerplexityConfig {
	return PerplexityConfig{
		Enabled:    v.Enabled,
		MaxResults: v.MaxResults,
		APIKeys:    toSecureStrings(mergeAPIKeys(v.APIKey, v.APIKeys)),
	}
}

type glmSearchConfigV0 struct {
	Enabled      bool   `json:"enabled"       env:"PICOCLAW_TOOLS_WEB_GLM_ENABLED"`
	APIKey       string `json:"api_key"       env:"PICOCLAW_TOOLS_WEB_GLM_API_KEY"`
	BaseURL      string `json:"base_url"      env:"PICOCLAW_TOOLS_WEB_GLM_BASE_URL"`
	SearchEngine string `json:"search_engine" env:"PICOCLAW_TOOLS_WEB_GLM_SEARCH_ENGINE"`
}

func (v *glmSearchConfigV0) ToGLMSearchConfig() GLMSearchConfig {
	return GLMSearchConfig{
		Enabled:      v.Enabled,
		APIKey:       *NewSecureString(v.APIKey),
		BaseURL:      v.BaseURL,
		SearchEngine: v.SearchEngine,
	}
}

type baiduSearchConfigV0 struct {
	Enabled    bool   `json:"enabled"     env:"PICOCLAW_TOOLS_WEB_BAIDU_ENABLED"`
	APIKey     string `json:"api_key"     env:"PICOCLAW_TOOLS_WEB_BAIDU_API_KEY"`
	BaseURL    string `json:"base_url"    env:"PICOCLAW_TOOLS_WEB_BAIDU_BASE_URL"`
	MaxResults int    `json:"max_results" env:"PICOCLAW_TOOLS_WEB_BAIDU_MAX_RESULTS"`
}

func (v *baiduSearchConfigV0) ToBaiduSearchConfig() BaiduSearchConfig {
	return BaiduSearchConfig{
		Enabled:    v.Enabled,
		APIKey:     *NewSecureString(v.APIKey),
		BaseURL:    v.BaseURL,
		MaxResults: v.MaxResults,
	}
}

func (v *webToolsConfigV0) ToWebToolsConfig() WebToolsConfig {
	brave := v.Brave.ToBraveConfig()
	tavily := v.Tavily.ToTavilyConfig()
	perplexity := v.Perplexity.ToPerplexityConfig()
	glmSearch := v.GLMSearch.ToGLMSearchConfig()
	baiduSearch := v.BaiduSearch.ToBaiduSearchConfig()

	return WebToolsConfig{
		ToolConfig:           v.ToolConfig,
		Brave:                brave,
		Tavily:               tavily,
		DuckDuckGo:           v.DuckDuckGo,
		Perplexity:           perplexity,
		SearXNG:              v.SearXNG,
		GLMSearch:            glmSearch,
		PreferNative:         v.PreferNative,
		Proxy:                v.Proxy,
		FetchLimitBytes:      v.FetchLimitBytes,
		Format:               v.Format,
		PrivateHostWhitelist: v.PrivateHostWhitelist,
		BaiduSearch:          baiduSearch,
	}
}

type skillsToolsConfigV0 struct {
	ToolConfig            `                         envPrefix:"PICOCLAW_TOOLS_SKILLS_"`
	Registries            skillsRegistriesConfigV0 `                                   json:"registries"`
	Github                skillsGithubConfigV0     `                                   json:"github"`
	MaxConcurrentSearches int                      `                                   json:"max_concurrent_searches" env:"PICOCLAW_TOOLS_SKILLS_MAX_CONCURRENT_SEARCHES"`
	SearchCache           SearchCacheConfig        `                                   json:"search_cache"`
}

type skillsRegistriesConfigV0 struct {
	ClawHub clawHubRegistryConfigV0 `json:"clawhub"`
}

type clawHubRegistryConfigV0 struct {
	Enabled    bool   `json:"enabled"     env:"PICOCLAW_SKILLS_REGISTRIES_CLAWHUB_ENABLED"`
	BaseURL    string `json:"base_url"    env:"PICOCLAW_SKILLS_REGISTRIES_CLAWHUB_BASE_URL"`
	AuthToken  string `json:"auth_token"  env:"PICOCLAW_SKILLS_REGISTRIES_CLAWHUB_AUTH_TOKEN"`
	SearchPath string `json:"search_path" env:"PICOCLAW_SKILLS_REGISTRIES_CLAWHUB_SEARCH_PATH"`
	SkillsPath string `json:"skills_path" env:"PICOCLAW_SKILLS_REGISTRIES_CLAWHUB_SKILLS_PATH"`
}

func (v *clawHubRegistryConfigV0) ToClawHubRegistryConfig() ClawHubRegistryConfig {
	cfg := ClawHubRegistryConfig{
		Enabled:    v.Enabled,
		BaseURL:    v.BaseURL,
		SearchPath: v.SearchPath,
		SkillsPath: v.SkillsPath,
	}
	if v.AuthToken != "" {
		cfg.AuthToken = *NewSecureString(v.AuthToken)
	}
	return cfg
}

type skillsGithubConfigV0 struct {
	Token string `json:"token"           env:"PICOCLAW_TOOLS_SKILLS_GITHUB_TOKEN"`
	Proxy string `json:"proxy,omitempty" env:"PICOCLAW_TOOLS_SKILLS_GITHUB_PROXY"`
}

func (v *skillsGithubConfigV0) ToSkillsGithubConfig() SkillsGithubConfig {
	return SkillsGithubConfig{
		Token: *NewSecureString(v.Token),
		Proxy: v.Proxy,
	}
}

func (v *skillsRegistriesConfigV0) ToSkillsRegistriesConfig() SkillsRegistriesConfig {
	clawHub := v.ClawHub.ToClawHubRegistryConfig()

	return SkillsRegistriesConfig{
		ClawHub: clawHub,
	}
}

func (v *skillsToolsConfigV0) ToSkillsToolsConfig() SkillsToolsConfig {
	registries := v.Registries.ToSkillsRegistriesConfig()
	github := v.Github.ToSkillsGithubConfig()
	return SkillsToolsConfig{
		ToolConfig:            v.ToolConfig,
		Registries:            registries,
		Github:                github,
		MaxConcurrentSearches: v.MaxConcurrentSearches,
		SearchCache:           v.SearchCache,
	}
}
