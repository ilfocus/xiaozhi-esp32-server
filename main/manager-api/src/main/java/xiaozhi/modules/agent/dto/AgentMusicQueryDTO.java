package xiaozhi.modules.agent.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;
import lombok.Data;

@Data
@Schema(description = "AI音乐查询请求")
public class AgentMusicQueryDTO {
    @Schema(description = "设备MAC地址", example = "00:11:22:33:44:55")
    @NotBlank
    private String macAddress;

    @Schema(description = "歌曲名关键词")
    private String keyword;

    @Schema(description = "返回数量")
    private Integer limit;
}
