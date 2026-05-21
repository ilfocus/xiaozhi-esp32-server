package xiaozhi.modules.agent.controller;

import java.util.List;

import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import xiaozhi.common.utils.Result;
import xiaozhi.modules.agent.dto.AgentMusicQueryDTO;
import xiaozhi.modules.agent.dto.AgentMusicSaveDTO;
import xiaozhi.modules.agent.service.AgentMusicService;
import xiaozhi.modules.agent.vo.AgentMusicVO;

@Tag(name = "AI音乐作品")
@RequiredArgsConstructor
@RestController
@RequestMapping("/agent/music")
public class AgentMusicController {
    private final AgentMusicService agentMusicService;

    @PostMapping("/save")
    @Operation(summary = "小智服务保存AI音乐作品")
    public Result<AgentMusicVO> saveFromServer(@Valid @RequestBody AgentMusicSaveDTO request) {
        return new Result<AgentMusicVO>().ok(agentMusicService.saveFromServer(request));
    }

    @PostMapping("/list")
    @Operation(summary = "小智服务查询AI音乐作品")
    public Result<List<AgentMusicVO>> listForServer(@Valid @RequestBody AgentMusicQueryDTO request) {
        return new Result<List<AgentMusicVO>>().ok(agentMusicService.listForServer(request));
    }
}
