/** Plain-language help for Reticulum interface types in RNSVG. */
export const RNSVG_INTERFACE_HELP = {
    TCPClientInterface:
        "Connect outbound to a remote Reticulum peer over TCP. Use when you know a community node's host and port.",
    TCPServerInterface:
        "Listen for inbound TCP connections so other nodes can connect to your machine as a backbone or hub.",
    UDPInterface:
        "UDP transport for low-latency LAN links. Both sides need matching IP, port, and optional password.",
    BackboneInterface:
        "Public relay mode for carrying transit traffic across the mesh. Enable only if you have bandwidth to share.",
    RNodeInterface:
        "LoRa radio via an RNode. Requires correct serial device, frequency, and bandwidth for your hardware.",
    RNodeMultiInterface:
        "Group of multiple RNode sub-interfaces on one host.",
    I2PInterface:
        "Tunnel Reticulum over I2P when direct internet paths are blocked or undesirable.",
    TunnelInterface:
        "Generic tunnel wrapping Reticulum inside another transport provided by external tooling.",
    SerialInterface:
        "Raw serial link to a modem or radio adapter. Set the correct device path and baud rate.",
    KISSInterface:
        "Packet-radio TNC using the KISS protocol — common for amateur radio gateways.",
    AutoInterface:
        "Automatic LAN discovery (multicast). Easiest way to find nearby peers on the same local network.",
    LocalInterface:
        "Loopback-only for testing on this machine. Does not reach other computers.",
    AX25KISSInterface: "AX.25 KISS for amateur packet radio networks.",
    PipeInterface: "Pipe data through an external program that speaks Reticulum's pipe format.",
    RNodeIPInterface: "RNode reached over IP instead of direct serial.",
    __external__: "Load a custom Reticulum interface module via interfacepath.",
};

export function helpForInterfaceType(type) {
    return RNSVG_INTERFACE_HELP[type] || "Configure this interface according to your network setup and Reticulum docs.";
}