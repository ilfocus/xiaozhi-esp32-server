package xiaozhi.modules.device.dto;

import com.fasterxml.jackson.core.JsonParser;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.DeserializationContext;
import com.fasterxml.jackson.databind.JsonDeserializer;
import com.fasterxml.jackson.databind.JsonNode;

import java.io.IOException;

/**
 * 自定义反序列化器：兼容 board 字段为字符串或对象两种格式。
 * 某些设备固件发送 "board":"esp32-s3"（纯字符串），
 * 新版本发送 "board":{"type":"esp32-s3","ssid":"...",...}（对象），
 * 此反序列化器同时支持两种格式。
 */
public class BoardInfoDeserializer extends JsonDeserializer<DeviceReportReqDTO.BoardInfo> {

    @Override
    public DeviceReportReqDTO.BoardInfo deserialize(JsonParser p, DeserializationContext ctxt)
            throws IOException, JsonProcessingException {
        JsonNode node = p.getCodec().readTree(p);

        // 如果是字符串，直接当 type 字段处理
        if (node.isTextual()) {
            DeviceReportReqDTO.BoardInfo info = new DeviceReportReqDTO.BoardInfo();
            info.setType(node.asText());
            return info;
        }

        // 如果是对象，手动解析字段（避免递归调用自身导致 StackOverflow）
        if (node.isObject()) {
            DeviceReportReqDTO.BoardInfo info = new DeviceReportReqDTO.BoardInfo();
            if (node.has("type")) info.setType(node.get("type").asText());
            if (node.has("ssid")) info.setSsid(node.get("ssid").asText());
            if (node.has("rssi")) info.setRssi(node.get("rssi").asInt());
            if (node.has("channel")) info.setChannel(node.get("channel").asInt());
            if (node.has("ip")) info.setIp(node.get("ip").asText());
            if (node.has("mac")) info.setMac(node.get("mac").asText());
            return info;
        }

        return null;
    }
}
