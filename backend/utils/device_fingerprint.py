
import wmi
import hashlib
import platform

class CompactDeviceID:
    def __init__(self):
        self.c = wmi.WMI()

    def _get_hardware_fingerprint(self):
        """获取核心硬件特征组合"""
        components = [
            self._safe_get(lambda: self.c.Win32_Processor()[0].ProcessorId),
            self._safe_get(lambda: self.c.Win32_BaseBoard()[0].SerialNumber),
            self._safe_get(lambda: self.c.Win32_BIOS()[0].SerialNumber),
            self._safe_get(lambda: next((d.SerialNumber for d in self.c.Win32_DiskDrive()), "")),
            platform.node()  # 主机名
        ]
        return ':'.join(filter(None, components))

    def _safe_get(self, func):
        """安全获取硬件信息"""
        try:
            return func().strip()
        except:
            return ""

    def get_compact_id(self):
        """生成32字符长度的设备ID"""
        fingerprint = self._get_hardware_fingerprint().encode()
        # 使用MD5生成128位哈希后取前32字符
        return hashlib.md5(fingerprint).hexdigest()[:32]

if __name__ == "__main__":
    print("设备唯一ID:", CompactDeviceID().get_compact_id())
