package xiaozhi.modules.agent.entity;

import java.util.Date;

import com.baomidou.mybatisplus.annotation.FieldFill;
import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableField;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

import io.swagger.v3.oas.annotations.media.Schema;
import lombok.Data;

@Data
@TableName("ai_agent_music")
@Schema(description = "AI音乐作品")
public class AgentMusicEntity {
    @TableId(type = IdType.ASSIGN_UUID)
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

    @Schema(description = "状态：saved/deleted")
    private String status;

    @Schema(description = "创建者")
    @TableField(fill = FieldFill.INSERT)
    private Long creator;

    @Schema(description = "创建时间")
    @TableField(fill = FieldFill.INSERT)
    private Date createDate;

    @Schema(description = "更新者")
    @TableField(fill = FieldFill.UPDATE)
    private Long updater;

    @Schema(description = "更新时间")
    @TableField(fill = FieldFill.UPDATE)
    private Date updateDate;
}
