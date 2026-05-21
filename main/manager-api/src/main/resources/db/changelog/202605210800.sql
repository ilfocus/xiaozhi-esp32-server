CREATE TABLE IF NOT EXISTS `ai_agent_music` (
  `id` varchar(64) NOT NULL COMMENT '歌曲ID',
  `user_id` bigint NOT NULL COMMENT '用户ID',
  `agent_id` varchar(64) DEFAULT NULL COMMENT '智能体ID',
  `mac_address` varchar(64) NOT NULL COMMENT '设备MAC地址',
  `title` varchar(255) NOT NULL COMMENT '歌曲标题',
  `lyrics` text COMMENT '歌词',
  `style` varchar(255) DEFAULT NULL COMMENT '音乐风格',
  `prompt` text COMMENT '用户原始创作需求',
  `file_path` varchar(1024) NOT NULL COMMENT '服务端文件路径',
  `file_ext` varchar(16) DEFAULT NULL COMMENT '文件格式',
  `provider` varchar(64) DEFAULT NULL COMMENT 'AI音乐服务商',
  `provider_task_id` varchar(255) DEFAULT NULL COMMENT '服务商任务ID',
  `status` varchar(32) NOT NULL DEFAULT 'saved' COMMENT '状态：saved/deleted',
  `creator` bigint DEFAULT NULL COMMENT '创建者',
  `create_date` datetime DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updater` bigint DEFAULT NULL COMMENT '更新者',
  `update_date` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_ai_agent_music_user_status` (`user_id`, `status`, `create_date`),
  KEY `idx_ai_agent_music_mac` (`mac_address`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='AI音乐作品表';

SET @data_exists = (SELECT COUNT(*) FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_AI_MUSIC');
SET @sql = IF(@data_exists = 0,
    'INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES (''SYSTEM_PLUGIN_AI_MUSIC'', ''Plugin'', ''ai_music'', ''AI音乐创作'', ''[{\"key\":\"provider\",\"type\":\"string\",\"label\":\"Provider：mock / generic_http\",\"default\":\"mock\",\"editing\":false,\"selected\":false},{\"key\":\"output_dir\",\"type\":\"string\",\"label\":\"生成音乐保存目录\",\"default\":\"data/generated_music\",\"editing\":false,\"selected\":false},{\"key\":\"base_url\",\"type\":\"string\",\"label\":\"AI音乐API地址\",\"default\":\"\",\"editing\":false,\"selected\":false},{\"key\":\"api_key\",\"type\":\"string\",\"label\":\"AI音乐API Key\",\"default\":\"\",\"editing\":false,\"selected\":false},{\"key\":\"generate_endpoint\",\"type\":\"string\",\"label\":\"生成接口路径\",\"default\":\"\",\"editing\":false,\"selected\":false}]'', 85, 0, NOW(), 0, NOW())',
    'SELECT ''data already exists, skip'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @data_exists = (SELECT COUNT(*) FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_SAVE_AI_MUSIC');
SET @sql = IF(@data_exists = 0,
    'INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES (''SYSTEM_PLUGIN_SAVE_AI_MUSIC'', ''Plugin'', ''save_ai_music'', ''保存AI音乐'', JSON_ARRAY(), 86, 0, NOW(), 0, NOW())',
    'SELECT ''data already exists, skip'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @data_exists = (SELECT COUNT(*) FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_REDO_AI_MUSIC');
SET @sql = IF(@data_exists = 0,
    'INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES (''SYSTEM_PLUGIN_REDO_AI_MUSIC'', ''Plugin'', ''redo_ai_music'', ''重做AI音乐'', JSON_ARRAY(), 87, 0, NOW(), 0, NOW())',
    'SELECT ''data already exists, skip'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;

SET @data_exists = (SELECT COUNT(*) FROM ai_model_provider WHERE id = 'SYSTEM_PLUGIN_PLAY_MY_MUSIC');
SET @sql = IF(@data_exists = 0,
    'INSERT INTO `ai_model_provider` (`id`, `model_type`, `provider_code`, `name`, `fields`, `sort`, `creator`, `create_date`, `updater`, `update_date`) VALUES (''SYSTEM_PLUGIN_PLAY_MY_MUSIC'', ''Plugin'', ''play_my_music'', ''播放已保存AI音乐'', JSON_ARRAY(), 88, 0, NOW(), 0, NOW())',
    'SELECT ''data already exists, skip'' AS msg');
PREPARE stmt FROM @sql; EXECUTE stmt; DEALLOCATE PREPARE stmt;
