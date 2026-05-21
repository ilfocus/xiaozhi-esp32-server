package xiaozhi.modules.agent.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
@Schema(description = "AI音乐保存请求")
public class AgentMusicSaveDTO {
    @Schema(description = "设备MAC地址", example = "00:11:22:33:44:55")
    @NotBlank
    private String macAddress;

    @Schema(description = "歌曲标题")
    @NotBlank
    private String title;

    @Schema(description = "歌词")
    private String lyrics;

    @Schema(description = "音乐风格")
    private String style;

    @Schema(description = "用户原始创作需求")
    private String prompt;

    @Schema(description = "服务端文件路径")
    @NotBlank
    private String filePath;

    @Schema(description = "文件格式")
    private String fileExt;

    @Schema(description = "AI音乐服务商")
    private String provider;

    @Schema(description = "服务商任务ID")
    private String providerTaskId;
}
