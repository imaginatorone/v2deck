import {
  definePlugin,
  PanelSection,
  PanelSectionRow,
  ButtonItem,
  ToggleField,
  TextField,
  SliderField,
  DropdownItem,
  showModal,
  ModalRoot,
  DialogButton,
  Focusable,
  staticClasses
} from "@decky/ui";
import { call, toaster } from "@decky/api";
import { useState, useEffect, FC } from "react";
import { FaShieldAlt, FaPlus, FaTrash, FaGlobe, FaPlug, FaCog, FaCheck, FaTerminal, FaSync, FaDownload, FaExclamationTriangle } from "react-icons/fa";

interface VLESSProfile {
  name: string;
  uuid: string;
  address: string;
  port: number;
  network: string;
  security: string;
  [key: string]: unknown;
}

interface Settings {
  mode: string;
  socks_port: number;
  http_port: number;
  log_level: string;
  domain_strategy: string;
  allow_insecure: boolean;
  mux_enabled: boolean;
  mux_concurrency: number;
  block_ads: boolean;
  bypass_lan: boolean;
  bypass_cn: boolean;
  custom_dns: string;
  tun_mtu: number;
}

interface ConnectionStatus {
  connected: boolean;
  mode: string;
  profile: VLESSProfile | null;
}

interface DepsStatus {
  xray_installed: boolean;
  tun2socks_installed: boolean;
  all_installed: boolean;
  xray_version: string;
  tun2socks_version: string;
}

const ProfileCard: FC<{
  profile: VLESSProfile;
  isActive: boolean;
  onConnect: () => void;
  onDelete: () => void;
}> = ({ profile, isActive, onConnect, onDelete }) => (
  <Focusable style={{
    display: "flex",
    padding: "10px",
    marginBottom: "6px",
    backgroundColor: isActive ? "rgba(0, 200, 83, 0.2)" : "rgba(255, 255, 255, 0.05)",
    borderRadius: "6px",
    border: isActive ? "1px solid #00c853" : "1px solid rgba(255, 255, 255, 0.1)"
  }}>
    <div style={{ flex: 1 }}>
      <div style={{ fontWeight: "bold", fontSize: "13px" }}>{profile.name}</div>
      <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)" }}>
        {profile.address}:{profile.port} · {profile.security}/{profile.network}
      </div>
    </div>
    <div style={{ display: "flex", gap: "6px" }}>
      <DialogButton style={{ minWidth: "36px", padding: "6px" }} onClick={onConnect} disabled={isActive}>
        {isActive ? <FaCheck /> : <FaPlug />}
      </DialogButton>
      <DialogButton style={{ minWidth: "36px", padding: "6px" }} onClick={onDelete}>
        <FaTrash />
      </DialogButton>
    </div>
  </Focusable>
);

const AddProfileModal: FC<{ closeModal: () => void; onAdded: () => void }> = ({ closeModal, onAdded }) => {
  const [uri, setUri] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleImport = async () => {
    if (!uri.trim() || !uri.startsWith("vless://")) {
      setError("Enter valid vless:// URI");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const result = await call<[string], { success: boolean; error?: string }>("import_from_uri", uri.trim());
      if (result.success) {
        toaster.toast({ title: "v2deck", body: "Profile added" });
        onAdded();
        closeModal();
      } else {
        setError(result.error || "Import failed");
      }
    } catch (e) {
      setError(`Error: ${e}`);
    }
    setLoading(false);
  };

  return (
    <ModalRoot closeModal={closeModal}>
      <div style={{ padding: "16px", minWidth: "380px" }}>
        <h3 style={{ marginBottom: "12px" }}>Add Profile</h3>
        <TextField value={uri} onChange={(e) => setUri(e.target.value)} style={{ width: "100%", marginBottom: "8px" }} />
        {error && <div style={{ color: "#ff6b6b", fontSize: "12px", marginBottom: "8px" }}>{error}</div>}
        <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.4)", marginBottom: "12px" }}>
          Paste vless:// URI. Get it from v2rayNG, Nekobox, etc.
        </div>
        <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
          <DialogButton onClick={closeModal}>Cancel</DialogButton>
          <DialogButton onClick={handleImport} disabled={loading}>{loading ? "..." : "Import"}</DialogButton>
        </div>
      </div>
    </ModalRoot>
  );
};

const NerdStuffModal: FC<{ closeModal: () => void; settings: Settings; onSave: (s: Settings) => void }> = ({ closeModal, settings, onSave }) => {
  const [s, setS] = useState<Settings>({ ...settings });

  const update = <K extends keyof Settings>(key: K, val: Settings[K]) => setS({ ...s, [key]: val });

  const handleSave = async () => {
    await call<[Settings], { success: boolean }>("set_settings", s);
    onSave(s);
    toaster.toast({ title: "v2deck", body: "Settings saved" });
    closeModal();
  };

  const handleReset = async () => {
    const result = await call<[], { success: boolean; settings: Settings }>("reset_settings");
    if (result.success) {
      setS(result.settings);
      toaster.toast({ title: "v2deck", body: "Settings reset to defaults" });
    }
  };

  return (
    <ModalRoot closeModal={closeModal}>
      <div style={{ padding: "16px", minWidth: "400px", maxHeight: "70vh", overflowY: "auto" }}>
        <h3 style={{ marginBottom: "16px" }}><FaTerminal style={{ marginRight: "8px" }} />Nerd Stuff</h3>

        <div style={{ marginBottom: "16px" }}>
          <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.6)", marginBottom: "8px" }}>Connection Mode</div>
          <Focusable style={{ display: "flex", gap: "8px" }}>
            <DialogButton onClick={() => update("mode", "tun")} style={{ flex: 1, backgroundColor: s.mode === "tun" ? "rgba(0,200,83,0.3)" : "rgba(255,255,255,0.1)" }}>TUN</DialogButton>
            <DialogButton onClick={() => update("mode", "proxy")} style={{ flex: 1, backgroundColor: s.mode === "proxy" ? "rgba(0,200,83,0.3)" : "rgba(255,255,255,0.1)" }}>Proxy</DialogButton>
          </Focusable>
        </div>

        <div style={{ marginBottom: "12px" }}>
          <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.6)", marginBottom: "4px" }}>SOCKS Port</div>
          <SliderField value={s.socks_port} min={1024} max={65535} step={1} onChange={(v) => update("socks_port", v)} showValue />
        </div>

        <div style={{ marginBottom: "12px" }}>
          <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.6)", marginBottom: "4px" }}>HTTP Port</div>
          <SliderField value={s.http_port} min={1024} max={65535} step={1} onChange={(v) => update("http_port", v)} showValue />
        </div>

        <div style={{ marginBottom: "12px" }}>
          <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.6)", marginBottom: "4px" }}>TUN MTU</div>
          <SliderField value={s.tun_mtu} min={1280} max={9000} step={10} onChange={(v) => update("tun_mtu", v)} showValue />
        </div>

        <div style={{ marginBottom: "12px" }}>
          <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.6)", marginBottom: "4px" }}>DNS Server</div>
          <TextField value={s.custom_dns} onChange={(e) => update("custom_dns", e.target.value)} />
        </div>

        <div style={{ marginBottom: "12px" }}>
          <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.6)", marginBottom: "4px" }}>Log Level</div>
          <DropdownItem
            rgOptions={[
              { data: "none", label: "None" },
              { data: "error", label: "Error" },
              { data: "warning", label: "Warning" },
              { data: "info", label: "Info" },
              { data: "debug", label: "Debug" }
            ]}
            selectedOption={s.log_level}
            onChange={(opt) => update("log_level", opt.data)}
          />
        </div>

        <div style={{ marginBottom: "12px" }}>
          <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.6)", marginBottom: "4px" }}>Domain Strategy</div>
          <DropdownItem
            rgOptions={[
              { data: "AsIs", label: "AsIs" },
              { data: "IPIfNonMatch", label: "IPIfNonMatch" },
              { data: "IPOnDemand", label: "IPOnDemand" }
            ]}
            selectedOption={s.domain_strategy}
            onChange={(opt) => update("domain_strategy", opt.data)}
          />
        </div>

        <div style={{ marginBottom: "8px" }}>
          <ToggleField label="Block Ads" checked={s.block_ads} onChange={(v) => update("block_ads", v)} />
        </div>
        <div style={{ marginBottom: "8px" }}>
          <ToggleField label="Bypass LAN" checked={s.bypass_lan} onChange={(v) => update("bypass_lan", v)} />
        </div>
        <div style={{ marginBottom: "8px" }}>
          <ToggleField label="Bypass China" checked={s.bypass_cn} onChange={(v) => update("bypass_cn", v)} />
        </div>
        <div style={{ marginBottom: "8px" }}>
          <ToggleField label="Allow Insecure TLS" checked={s.allow_insecure} onChange={(v) => update("allow_insecure", v)} />
        </div>
        <div style={{ marginBottom: "8px" }}>
          <ToggleField label="Enable Mux" checked={s.mux_enabled} onChange={(v) => update("mux_enabled", v)} />
        </div>
        {s.mux_enabled && (
          <div style={{ marginBottom: "12px" }}>
            <div style={{ fontSize: "12px", color: "rgba(255,255,255,0.6)", marginBottom: "4px" }}>Mux Concurrency</div>
            <SliderField value={s.mux_concurrency} min={1} max={16} step={1} onChange={(v) => update("mux_concurrency", v)} showValue />
          </div>
        )}

        <div style={{ display: "flex", gap: "8px", justifyContent: "space-between", marginTop: "16px" }}>
          <DialogButton onClick={handleReset}><FaSync style={{ marginRight: "4px" }} />Reset</DialogButton>
          <div style={{ display: "flex", gap: "8px" }}>
            <DialogButton onClick={closeModal}>Cancel</DialogButton>
            <DialogButton onClick={handleSave}>Save</DialogButton>
          </div>
        </div>
      </div>
    </ModalRoot>
  );
};

const LogsModal: FC<{ closeModal: () => void }> = ({ closeModal }) => {
  const [logs, setLogs] = useState("Loading...");

  useEffect(() => {
    (async () => {
      const result = await call<[number], { success: boolean; logs?: string }>("get_logs", 100);
      setLogs(result.success ? (result.logs || "No logs") : "Failed to load logs");
    })();
  }, []);

  return (
    <ModalRoot closeModal={closeModal}>
      <div style={{ padding: "16px", minWidth: "400px" }}>
        <h3 style={{ marginBottom: "12px" }}>Xray Logs</h3>
        <pre style={{ fontSize: "10px", maxHeight: "300px", overflow: "auto", backgroundColor: "rgba(0,0,0,0.3)", padding: "8px", borderRadius: "4px", whiteSpace: "pre-wrap", wordBreak: "break-all" }}>
          {logs}
        </pre>
        <div style={{ marginTop: "12px", textAlign: "right" }}>
          <DialogButton onClick={closeModal}>Close</DialogButton>
        </div>
      </div>
    </ModalRoot>
  );
};

const DepsBanner: FC<{ deps: DepsStatus; onInstall: () => void; installing: boolean }> = ({ deps, onInstall, installing }) => {
  if (deps.all_installed) return null;

  return (
    <PanelSection>
      <PanelSectionRow>
        <div style={{
          padding: "12px",
          backgroundColor: "rgba(255, 193, 7, 0.15)",
          borderRadius: "8px",
          border: "1px solid rgba(255, 193, 7, 0.3)"
        }}>
          <div style={{ display: "flex", alignItems: "center", marginBottom: "8px" }}>
            <FaExclamationTriangle style={{ color: "#ffc107", marginRight: "8px" }} />
            <span style={{ fontWeight: "bold" }}>Dependencies Required</span>
          </div>
          <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.6)", marginBottom: "10px" }}>
            {!deps.xray_installed && <div>xray-core v{deps.xray_version}</div>}
            {!deps.tun2socks_installed && <div>tun2socks v{deps.tun2socks_version}</div>}
          </div>
          <ButtonItem layout="below" onClick={onInstall} disabled={installing}>
            <FaDownload style={{ marginRight: "6px" }} />
            {installing ? "Installing..." : "Install Dependencies"}
          </ButtonItem>
        </div>
      </PanelSectionRow>
    </PanelSection>
  );
};

const Content: FC = () => {
  const [profiles, setProfiles] = useState<VLESSProfile[]>([]);
  const [status, setStatus] = useState<ConnectionStatus>({ connected: false, mode: "tun", profile: null });
  const [settings, setSettings] = useState<Settings | null>(null);
  const [deps, setDeps] = useState<DepsStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [publicIP, setPublicIP] = useState("");

  const load = async () => {
    const [profilesRes, statusRes, settingsRes, depsRes] = await Promise.all([
      call<[], { success: boolean; profiles: VLESSProfile[] }>("load_profiles"),
      call<[], ConnectionStatus>("get_status"),
      call<[], { success: boolean; settings: Settings }>("get_settings"),
      call<[], DepsStatus & { success: boolean }>("check_dependencies")
    ]);
    if (profilesRes.success) setProfiles(profilesRes.profiles);
    setStatus(statusRes);
    if (settingsRes.success) setSettings(settingsRes.settings);
    if (depsRes.success) setDeps(depsRes);
  };

  const fetchIP = async () => {
    const result = await call<[], { success: boolean; ip?: string }>("get_public_ip");
    if (result.success && result.ip) setPublicIP(result.ip);
  };

  useEffect(() => {
    load();
    fetchIP();
    const interval = setInterval(() => call<[], ConnectionStatus>("get_status").then(setStatus), 5000);
    return () => clearInterval(interval);
  }, []);

  const handleInstallDeps = async () => {
    setInstalling(true);
    toaster.toast({ title: "v2deck", body: "Downloading dependencies..." });

    const result = await call<[], { success: boolean; error?: string; message?: string }>("install_dependencies");

    if (result.success) {
      toaster.toast({ title: "v2deck", body: "Dependencies installed!" });
      await load();
    } else {
      toaster.toast({ title: "Error", body: result.error || "Installation failed" });
    }
    setInstalling(false);
  };

  const handleConnect = async (profile: VLESSProfile) => {
    if (deps && !deps.all_installed) {
      toaster.toast({ title: "v2deck", body: "Install dependencies first" });
      return;
    }
    setLoading(true);
    const result = await call<[VLESSProfile], { success: boolean; error?: string }>("connect", profile);
    if (result.success) {
      toaster.toast({ title: "v2deck", body: `Connected to ${profile.name}` });
      await load();
      await fetchIP();
    } else {
      toaster.toast({ title: "Error", body: result.error || "Failed" });
    }
    setLoading(false);
  };

  const handleDisconnect = async () => {
    setLoading(true);
    await call<[], { success: boolean }>("disconnect");
    toaster.toast({ title: "v2deck", body: "Disconnected" });
    await load();
    await fetchIP();
    setLoading(false);
  };

  const handleDelete = async (profile: VLESSProfile) => {
    await call<[string], { success: boolean }>("delete_profile", profile.name);
    toaster.toast({ title: "v2deck", body: "Deleted" });
    await load();
  };

  const handleTest = async () => {
    const result = await call<[], { success: boolean; error?: string }>("test_connection");
    toaster.toast({ title: "v2deck", body: result.success ? "OK" : (result.error || "Failed") });
  };

  return (
    <div>
      {/* Dependencies Banner */}
      {deps && <DepsBanner deps={deps} onInstall={handleInstallDeps} installing={installing} />}

      <PanelSection title="Status">
        <PanelSectionRow>
          <div style={{ display: "flex", alignItems: "center", padding: "10px", backgroundColor: status.connected ? "rgba(0,200,83,0.15)" : "rgba(255,255,255,0.05)", borderRadius: "6px" }}>
            <div style={{ width: "10px", height: "10px", borderRadius: "50%", backgroundColor: status.connected ? "#00c853" : "#ff5252", marginRight: "10px" }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: "bold" }}>{status.connected ? "Connected" : "Disconnected"}</div>
              {status.connected && status.profile && <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)" }}>{status.profile.name} · {status.mode.toUpperCase()}</div>}
            </div>
          </div>
        </PanelSectionRow>
        {publicIP && (
          <PanelSectionRow>
            <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.5)" }}><FaGlobe style={{ marginRight: "6px" }} />IP: {publicIP}</div>
          </PanelSectionRow>
        )}
        {status.connected && (
          <PanelSectionRow>
            <Focusable style={{ display: "flex", gap: "8px" }}>
              <ButtonItem layout="below" onClick={handleDisconnect} disabled={loading}>Disconnect</ButtonItem>
              <ButtonItem layout="below" onClick={handleTest}>Test</ButtonItem>
            </Focusable>
          </PanelSectionRow>
        )}
      </PanelSection>

      <PanelSection title="Profiles">
        {profiles.length === 0 ? (
          <PanelSectionRow>
            <div style={{ textAlign: "center", padding: "16px", color: "rgba(255,255,255,0.4)", fontSize: "12px" }}>No profiles. Add one below.</div>
          </PanelSectionRow>
        ) : (
          profiles.map((p, i) => (
            <PanelSectionRow key={i}>
              <ProfileCard profile={p} isActive={status.connected && status.profile?.name === p.name} onConnect={() => handleConnect(p)} onDelete={() => handleDelete(p)} />
            </PanelSectionRow>
          ))
        )}
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => showModal(<AddProfileModal closeModal={() => {}} onAdded={load} />)}>
            <FaPlus style={{ marginRight: "6px" }} />Add Profile
          </ButtonItem>
        </PanelSectionRow>
      </PanelSection>

      <PanelSection title="Settings">
        <PanelSectionRow>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontSize: "13px" }}>Mode: {settings?.mode?.toUpperCase() || "TUN"}</div>
              <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.4)" }}>SOCKS:{settings?.socks_port} HTTP:{settings?.http_port}</div>
            </div>
            <ButtonItem layout="below" onClick={() => settings && showModal(<NerdStuffModal closeModal={() => {}} settings={settings} onSave={(s) => { setSettings(s); setStatus({ ...status, mode: s.mode }); }} />)}>
              <FaCog />
            </ButtonItem>
          </div>
        </PanelSectionRow>
        <PanelSectionRow>
          <ButtonItem layout="below" onClick={() => showModal(<LogsModal closeModal={() => {}} />)}>
            <FaTerminal style={{ marginRight: "6px" }} />View Logs
          </ButtonItem>
        </PanelSectionRow>
        {deps?.all_installed && (
          <PanelSectionRow>
            <div style={{ fontSize: "10px", color: "rgba(255,255,255,0.3)" }}>
              xray v{deps.xray_version} · tun2socks v{deps.tun2socks_version}
            </div>
          </PanelSectionRow>
        )}
      </PanelSection>
    </div>
  );
};

export default definePlugin(() => ({
  name: "v2deck",
  title: <div className={staticClasses.Title}>v2deck</div>,
  content: <Content />,
  icon: <FaShieldAlt />,
  onDismount() {}
}));
