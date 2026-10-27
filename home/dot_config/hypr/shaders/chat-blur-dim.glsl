#version 320 es
// @duration 0.20
precision highp float;
in vec2 v_texcoord;
out vec4 fragColor;
uniform sampler2D tex;
uniform vec2 surface_size;
uniform float progress;
uniform float is_active;

float coverageAt(vec2 uv) {
    vec4 sampleColour = texture(tex, uv);
    vec3 colour = sampleColour.rgb;
    return smoothstep(0.20, 0.50, dot(colour, vec3(0.2126, 0.7152, 0.0722)));
}

void main() {
    // These chat main windows are opaque; RGBX buffers need not carry alpha.
    vec4 source = vec4(texture(tex, v_texcoord).rgb, 1.0);
    // Use the plugin's logical surface size: imported client buffers need not
    // expose a useful textureSize query. Blur coverage, not input luminance,
    // so thin text survives the threshold. A 1.2px 3x3 Gaussian softens edges.
    vec2 offset = 1.2 / max(surface_size, vec2(1.0));
    float luminance = (4.0 * coverageAt(v_texcoord)
        + 2.0 * coverageAt(v_texcoord + vec2(offset.x, 0.0))
        + 2.0 * coverageAt(v_texcoord - vec2(offset.x, 0.0))
        + 2.0 * coverageAt(v_texcoord + vec2(0.0, offset.y))
        + 2.0 * coverageAt(v_texcoord - vec2(0.0, offset.y))
        + coverageAt(v_texcoord + offset)
        + coverageAt(v_texcoord - offset)
        + coverageAt(v_texcoord + vec2(offset.x, -offset.y))
        + coverageAt(v_texcoord + vec2(-offset.x, offset.y))) / 16.0;
    float ink = luminance;
    // Rosé Punk panel background (#1f1d2e) and foreground (#e5e5e5).
    vec3 background = vec3(31.0, 29.0, 46.0) / 255.0;
    vec3 foreground = vec3(229.0) / 255.0;
    vec3 subdued = 0.8 * mix(background, foreground, ink);
    float eased = smoothstep(0.0, 1.0, progress);
    float amount = is_active > 0.5 ? 1.0 - eased : eased;
    fragColor = vec4(mix(source.rgb, subdued, amount), 1.0);
}
