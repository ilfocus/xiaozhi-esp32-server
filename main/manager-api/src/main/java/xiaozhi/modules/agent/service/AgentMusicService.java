package xiaozhi.modules.agent.service;

import java.util.List;

import com.baomidou.mybatisplus.extension.service.IService;
import xiaozhi.modules.agent.dto.AgentMusicQueryDTO;
import xiaozhi.modules.agent.dto.AgentMusicSaveDTO;
import xiaozhi.modules.agent.entity.AgentMusicEntity;
import xiaozhi.modules.agent.vo.AgentMusicVO;

public interface AgentMusicService extends IService<AgentMusicEntity> {
    AgentMusicVO saveFromServer(AgentMusicSaveDTO dto);

    List<AgentMusicVO> listForServer(AgentMusicQueryDTO dto);
}
