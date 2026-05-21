package xiaozhi.modules.agent.vo;

import java.util.Date;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@Schema(description = "AI音乐作品")
public class AgentMusicVO {
    @Schema(description = "歌曲ID")
    private String id;

    @Schema(description = "用户ID")
    private Long userId;

    @Schema(description = "智能体ID")
    private String agentId;

    @Schema(description = "设备MAC地址")
    private String macAddress;

    @Schema(description = "歌曲标题")
    private String title;

    @Schema(description = "歌词")
    private String lyrics;

    @Schema(description = "音乐风格")
    private String style;

    @Schema(description = "用户原始创作需求")
    private String prompt;

    @Schema(description = "服务端文件路径")
    private String filePath;

    @Schema(description = "文件格式")
    private String fileExt;

    @Schema(description = "AI音乐服务商")
    private String provider;

    @Schema(description = "服务商任务ID")
    private String providerTaskId;

    @Schema(description = "状态")
    private String status;

    @Schema(description = "创建时间")
    private Date createDate;
}
