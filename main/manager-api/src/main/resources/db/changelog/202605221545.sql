SET @old_ai_music_api_key = (
  SELECT JSON_UNQUOTE(JSON_EXTRACT(param_info, '$.api_key'))
  FROM ai_agent_plugin_mapping
  WHERE plugin_id = 'SYSTEM_PLUGIN_AI_MUSIC'
    AND JSON_EXTRACT(param_info, '$.api_key') IS NOT NULL
    AND JSON_UNQUOTE(JSON_EXTRACT(param_info, '$.api_key')) <> ''
  ORDER BY id DESC
  LIMIT 1
);

INSERT INTO `ai_model_provider` (
  `id`, `model_type`, `provider_code`, `name`, `fields`, `sort`,
  `creator`, `create_date`, `updater`, `update_date`
) VALUES (
  'SYSTEM_AI_MUSIC_minimax',
  'AI_MUSIC',
  'minimax',
  'MiniMax AI音乐生成',
  '[
    {"key":"base_url","type":"string","label":"基础URL"},
    {"key":"api_key","type":"string","label":"API密钥"},
    {"key":"model","type":"string","label":"音乐模型"},
    {"key":"auto_generate_lyrics","type":"boolean","label":"自动生成歌词"},
    {"key":"lyrics_optimizer","type":"boolean","label":"由MiniMax优化歌词"},
    {"key":"sample_rate","type":"number","label":"采样率"},
    {"key":"bitrate","type":"number","label":"码率"},
    {"key":"format","type":"string","label":"音频格式"},
    {"key":"request_timeout","type":"number","label":"请求超时秒数"}
  ]',
  1,
  0,
  NOW(),
  0,
  NOW()
) ON DUPLICATE KEY UPDATE
  `model_type` = VALUES(`model_type`),
  `provider_code` = VALUES(`provider_code`),
  `name` = VALUES(`name`),
  `fields` = VALUES(`fields`),
  `update_date` = NOW();

INSERT INTO `ai_model_config` (
  `id`, `model_type`, `model_code`, `model_name`, `is_default`, `is_enabled`,
  `config_json`, `doc_link`, `remark`, `sort`, `creator`, `create_date`, `updater`, `update_date`
) VALUES (
  'AI_MUSIC_MiniMax',
  'AI_MUSIC',
  'minimax',
  'MiniMax Music 2.6',
  1,
  1,
  JSON_OBJECT(
    'type', 'minimax',
    'provider', 'minimax',
    'base_url', 'https://api.minimaxi.com',
    'api_key', COALESCE(@old_ai_music_api_key, ''),
    'model', 'music-2.6',
    'auto_generate_lyrics', true,
    'lyrics_optimizer', false,
    'sample_rate', 44100,
    'bitrate', 256000,
    'format', 'mp3',
    'request_timeout', 300
  ),
  'https://platform.minimaxi.com/docs/guides/music-generation',
  'MiniMax AI音乐生成模型配置，供AI音乐创作插件引用',
  1,
  0,
  NOW(),
  0,
  NOW()
) ON DUPLICATE KEY UPDATE
  `model_type` = VALUES(`model_type`),
  `model_code` = VALUES(`model_code`),
  `model_name` = VALUES(`model_name`),
  `is_enabled` = 1,
  `config_json` = JSON_SET(
    `config_json`,
    '$.type', 'minimax',
    '$.provider', 'minimax',
    '$.base_url', COALESCE(JSON_UNQUOTE(JSON_EXTRACT(`config_json`, '$.base_url')), 'https://api.minimaxi.com'),
    '$.api_key', COALESCE(NULLIF(JSON_UNQUOTE(JSON_EXTRACT(`config_json`, '$.api_key')), ''), @old_ai_music_api_key, ''),
    '$.model', COALESCE(JSON_UNQUOTE(JSON_EXTRACT(`config_json`, '$.model')), 'music-2.6'),
    '$.auto_generate_lyrics', COALESCE(JSON_EXTRACT(`config_json`, '$.auto_generate_lyrics'), true),
    '$.lyrics_optimizer', COALESCE(JSON_EXTRACT(`config_json`, '$.lyrics_optimizer'), false),
    '$.sample_rate', COALESCE(JSON_EXTRACT(`config_json`, '$.sample_rate'), 44100),
    '$.bitrate', COALESCE(JSON_EXTRACT(`config_json`, '$.bitrate'), 256000),
    '$.format', COALESCE(JSON_UNQUOTE(JSON_EXTRACT(`config_json`, '$.format')), 'mp3'),
    '$.request_timeout', COALESCE(JSON_EXTRACT(`config_json`, '$.request_timeout'), 300)
  ),
  `doc_link` = VALUES(`doc_link`),
  `remark` = VALUES(`remark`),
  `update_date` = NOW();

UPDATE `ai_model_provider`
SET `fields` = '[
  {"key":"ai_music_model_id","type":"string","label":"AI音乐模型配置ID","default":"AI_MUSIC_MiniMax","editing":false,"selected":false},
  {"key":"output_dir","type":"string","label":"生成音乐保存目录","default":"data/generated_music","editing":false,"selected":false},
  {"key":"default_style","type":"string","label":"默认曲风","default":"流行","editing":false,"selected":false},
  {"key":"initial_notice_delay","type":"number","label":"生成前提示等待秒数","default":1.5,"editing":false,"selected":false}
]',
    `update_date` = NOW()
WHERE `id` = 'SYSTEM_PLUGIN_AI_MUSIC';

UPDATE `ai_agent_plugin_mapping`
SET `param_info` = JSON_REMOVE(
  JSON_SET(
    COALESCE(`param_info`, JSON_OBJECT()),
    '$.ai_music_model_id',
    COALESCE(JSON_UNQUOTE(JSON_EXTRACT(`param_info`, '$.ai_music_model_id')), 'AI_MUSIC_MiniMax')
  ),
  '$.provider',
  '$.api_key',
  '$.base_url',
  '$.model',
  '$.generate_endpoint',
  '$.status_endpoint',
  '$.audio_url_field',
  '$.task_id_field',
  '$.status_field',
  '$.poll_interval',
  '$.timeout_seconds',
  '$.request_timeout',
  '$.auto_generate_lyrics',
  '$.lyrics_optimizer',
  '$.sample_rate',
  '$.bitrate',
  '$.format'
)
WHERE `plugin_id` = 'SYSTEM_PLUGIN_AI_MUSIC';
