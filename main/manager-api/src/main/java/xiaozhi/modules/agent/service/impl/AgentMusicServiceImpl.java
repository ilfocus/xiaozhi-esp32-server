package xiaozhi.modules.agent.service.impl;

import java.util.Date;
import java.util.List;

import org.apache.commons.lang3.StringUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;

import lombok.RequiredArgsConstructor;
import xiaozhi.common.exception.RenException;
import xiaozhi.common.utils.ConvertUtils;
import xiaozhi.modules.agent.dao.AgentMusicDao;
import xiaozhi.modules.agent.dto.AgentMusicQueryDTO;
import xiaozhi.modules.agent.dto.AgentMusicSaveDTO;
import xiaozhi.modules.agent.entity.AgentMusicEntity;
import xiaozhi.modules.agent.service.AgentMusicService;
import xiaozhi.modules.agent.vo.AgentMusicVO;
import xiaozhi.modules.device.entity.DeviceEntity;
import xiaozhi.modules.device.service.DeviceService;

@Service
@RequiredArgsConstructor
public class AgentMusicServiceImpl extends ServiceImpl<AgentMusicDao, AgentMusicEntity>
        implements AgentMusicService {
    private static final String STATUS_SAVED = "saved";

    private final DeviceService deviceService;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public AgentMusicVO saveFromServer(AgentMusicSaveDTO dto) {
        DeviceEntity device = getBoundDevice(dto.getMacAddress());

        AgentMusicEntity entity = new AgentMusicEntity();
        entity.setUserId(device.getUserId());
        entity.setAgentId(device.getAgentId());
        entity.setMacAddress(device.getMacAddress());
        entity.setTitle(dto.getTitle());
        entity.setLyrics(dto.getLyrics());
        entity.setStyle(dto.getStyle());
        entity.setPrompt(dto.getPrompt());
        entity.setFilePath(dto.getFilePath());
        entity.setFileExt(dto.getFileExt());
        entity.setProvider(dto.getProvider());
        entity.setProviderTaskId(dto.getProviderTaskId());
        entity.setStatus(STATUS_SAVED);
        entity.setCreator(device.getUserId());
        entity.setUpdater(device.getUserId());
        Date now = new Date();
        entity.setCreateDate(now);
        entity.setUpdateDate(now);
        save(entity);

        return ConvertUtils.sourceToTarget(entity, AgentMusicVO.class);
    }

    @Override
    public List<AgentMusicVO> listForServer(AgentMusicQueryDTO dto) {
        DeviceEntity device = getBoundDevice(dto.getMacAddress());
        int limit = dto.getLimit() == null || dto.getLimit() <= 0 ? 20 : Math.min(dto.getLimit(), 50);

        LambdaQueryWrapper<AgentMusicEntity> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(AgentMusicEntity::getUserId, device.getUserId())
                .eq(AgentMusicEntity::getStatus, STATUS_SAVED)
                .orderByDesc(AgentMusicEntity::getCreateDate)
                .last("LIMIT " + limit);
        if (StringUtils.isNotBlank(dto.getKeyword())) {
            wrapper.like(AgentMusicEntity::getTitle, dto.getKeyword());
        }

        return ConvertUtils.sourceToTarget(list(wrapper), AgentMusicVO.class);
    }

    private DeviceEntity getBoundDevice(String macAddress) {
        DeviceEntity device = deviceService.getDeviceByMacAddress(macAddress);
        if (device == null || device.getUserId() == null) {
            throw new RenException("设备未绑定用户，无法保存或查询AI歌曲");
        }
        return device;
    }
}
