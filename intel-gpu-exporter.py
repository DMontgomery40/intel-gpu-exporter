from prometheus_client import start_http_server, Gauge
import os
import re
import sys
import subprocess
import json
import logging

# Engine key compatibility helper (MTL/Xe vs legacy /0 keys)
# Returns first present value from candidate engine keys and coerces to float.
def eng_val(data, names, field):
    e = data.get("engines", {})
    for n in names:
        v = e.get(n, {}).get(field)
        if v is not None:
            try:
                return float(v)
            except Exception:
                pass
    return 0.0



igpu_device_id = Gauge(
    "igpu_device_id", "Intel GPU device id"
)

igpu_engines_blitter_0_busy = Gauge(
    "igpu_engines_blitter_0_busy", "Blitter 0 busy utilisation %"
)
igpu_engines_blitter_0_sema = Gauge(
    "igpu_engines_blitter_0_sema", "Blitter 0 sema utilisation %"
)
igpu_engines_blitter_0_wait = Gauge(
    "igpu_engines_blitter_0_wait", "Blitter 0 wait utilisation %"
)

igpu_engines_render_3d_0_busy = Gauge(
    "igpu_engines_render_3d_0_busy", "Render 3D 0 busy utilisation %"
)
igpu_engines_render_3d_0_sema = Gauge(
    "igpu_engines_render_3d_0_sema", "Render 3D 0 sema utilisation %"
)
igpu_engines_render_3d_0_wait = Gauge(
    "igpu_engines_render_3d_0_wait", "Render 3D 0 wait utilisation %"
)

igpu_engines_video_0_busy = Gauge(
    "igpu_engines_video_0_busy", "Video 0 busy utilisation %"
)
igpu_engines_video_0_sema = Gauge(
    "igpu_engines_video_0_sema", "Video 0 sema utilisation %"
)
igpu_engines_video_0_wait = Gauge(
    "igpu_engines_video_0_wait", "Video 0 wait utilisation %"
)

igpu_engines_video_enhance_0_busy = Gauge(
    "igpu_engines_video_enhance_0_busy", "Video Enhance 0 busy utilisation %"
)
igpu_engines_video_enhance_0_sema = Gauge(
    "igpu_engines_video_enhance_0_sema", "Video Enhance 0 sema utilisation %"
)
igpu_engines_video_enhance_0_wait = Gauge(
    "igpu_engines_video_enhance_0_wait", "Video Enhance 0 wait utilisation %"
)

igpu_frequency_actual = Gauge("igpu_frequency_actual", "Frequency actual MHz")
igpu_frequency_requested = Gauge("igpu_frequency_requested", "Frequency requested MHz")

igpu_imc_bandwidth_reads = Gauge("igpu_imc_bandwidth_reads", "IMC reads MiB/s")
igpu_imc_bandwidth_writes = Gauge("igpu_imc_bandwidth_writes", "IMC writes MiB/s")

igpu_interrupts = Gauge("igpu_interrupts", "Interrupts/s")

igpu_period = Gauge("igpu_period", "Period ms")

igpu_power_gpu = Gauge("igpu_power_gpu", "GPU power W")
igpu_power_package = Gauge("igpu_power_package", "Package power W")

igpu_rc6 = Gauge("igpu_rc6", "RC6 %")


def update(data):
    igpu_engines_blitter_0_busy.set(
        eng_val(data, ["Blitter/0", "Blitter"], "busy")
    )
    igpu_engines_blitter_0_sema.set(
        eng_val(data, ["Blitter/0", "Blitter"], "sema")
    )
    igpu_engines_blitter_0_wait.set(
        eng_val(data, ["Blitter/0", "Blitter"], "wait")
    )

    igpu_engines_render_3d_0_busy.set(
        eng_val(data, ["Render/3D/0", "Render/3D"], "busy")
    )
    igpu_engines_render_3d_0_sema.set(
        eng_val(data, ["Render/3D/0", "Render/3D"], "sema")
    )
    igpu_engines_render_3d_0_wait.set(
        eng_val(data, ["Render/3D/0", "Render/3D"], "wait")
    )

    igpu_engines_video_0_busy.set(
        eng_val(data, ["Video/0", "Video"], "busy")
    )
    igpu_engines_video_0_sema.set(
        eng_val(data, ["Video/0", "Video"], "sema")
    )
    igpu_engines_video_0_wait.set(
        eng_val(data, ["Video/0", "Video"], "wait")
    )

    igpu_engines_video_enhance_0_busy.set(
        eng_val(data, ["VideoEnhance/0", "VideoEnhance"], "busy")
    )
    igpu_engines_video_enhance_0_sema.set(
        eng_val(data, ["VideoEnhance/0", "VideoEnhance"], "sema")
    )
    igpu_engines_video_enhance_0_wait.set(
        eng_val(data, ["VideoEnhance/0", "VideoEnhance"], "wait")
    )

    igpu_frequency_actual.set(data.get("frequency", {}).get("actual", 0))
    igpu_frequency_requested.set(data.get("frequency", {}).get("requested", 0))

    igpu_imc_bandwidth_reads.set(data.get("imc-bandwidth", {}).get("reads", 0))
    igpu_imc_bandwidth_writes.set(data.get("imc-bandwidth", {}).get("writes", 0))

    igpu_interrupts.set(data.get("interrupts", {}).get("count", 0))

    igpu_period.set(data.get("period", {}).get("duration", 0))

    igpu_power_gpu.set(data.get("power", {}).get("GPU", 0))
    igpu_power_package.set(data.get("power", {}).get("Package", 0))

    igpu_rc6.set(data.get("rc6", {}).get("value", 0))


if __name__ == "__main__":
    if os.getenv("DEBUG", False):
        debug = logging.DEBUG
    else:
        debug = logging.INFO
    logging.basicConfig(format="%(asctime)s - %(message)s", level=debug)

    start_http_server(8080)

    period = os.getenv("REFRESH_PERIOD_MS", 1000)

    cmd = "intel_gpu_top -L"
    out, _ = subprocess.Popen(
        cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ).communicate()
    out = out.decode()

    device_id = "0x" + re.search(r"device=(\w+)", out.splitlines()[0]).groups()[0]
    device_id = int(device_id, 16)

    igpu_device_id.set(device_id)

    cmd = "intel_gpu_top -J -s {}".format(int(period))
    process = subprocess.Popen(
        cmd.split(), stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )

    logging.info("Started " + cmd)
    # Robust streaming JSON parse: bracket-depth framing
    buf = ''
    depth = 0
    started = False
    while True:
        chunk = process.stdout.read(4096)
        if not chunk:
            break
        for ch in chunk.decode('utf-8', 'ignore'):
            if not started:
                if ch == '{':
                    started = True
                    depth = 1
                    buf = '{'
            else:
                buf += ch
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        try:
                            data = json.loads(buf)
                            logging.debug(data)
                            update(data)
                        except Exception:
                            pass
                        buf = ''
                        started = False
process.kill()

    if process.returncode != 0:
        logging.error("Error: " + process.stderr.read().decode("utf-8"))

    logging.info("Finished")
