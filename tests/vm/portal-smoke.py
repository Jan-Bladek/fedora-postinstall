#!/usr/bin/env python3
"""Interactive ScreenCast/PipeWire frame test inside a disposable GUI guest."""
import os
from pathlib import Path
import uuid


def main():
    if os.environ.get('FEDORA_POSTINSTALL_TEST_TARGET') != 'disposable':
        raise SystemExit('Run only in a disposable VM with explicit screen-picker approval.')
    import gi
    gi.require_version('Gst', '1.0')
    gi.require_version('GstVideo', '1.0')
    from gi.repository import Gio, GLib, Gst, GstVideo
    Gst.init(None)
    bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
    destination = 'org.freedesktop.portal.Desktop'
    path = '/org/freedesktop/portal/desktop'
    interface = 'org.freedesktop.portal.ScreenCast'
    session = None
    remote_fd = None
    pipeline = None

    def request(method, signature, args, options):
        token = 'test_' + uuid.uuid4().hex
        options = dict(options, handle_token=GLib.Variant('s', token))
        expected = path + '/request/' + bus.get_unique_name()[1:].replace('.', '_') + '/' + token
        loop = GLib.MainLoop()
        response = []
        def receive(connection, sender, object_path, iface, signal, params, *unused):
            response.append(params.unpack())
            loop.quit()
        subscription = bus.signal_subscribe(destination, 'org.freedesktop.portal.Request',
                                            'Response', expected, None, Gio.DBusSignalFlags.NONE,
                                            receive)
        timer = GLib.timeout_add_seconds(120, lambda: (loop.quit(), False)[1])
        try:
            handle = bus.call_sync(destination, path, interface, method,
                          GLib.Variant(signature, (*args, options)), None,
                          Gio.DBusCallFlags.NONE, 120000, None).unpack()[0]
            print(method, 'request:', handle, flush=True)
            if handle != expected:
                raise RuntimeError('Portal ignored the request handle token')
            if not response:
                loop.run()
            if not response:
                raise TimeoutError(method + ': portal response timed out')
            code, results = response[0]
            print(method, 'response:', code, flush=True)
            if code != 0:
                raise RuntimeError(method + ': screen sharing was not approved')
            return results
        finally:
            bus.signal_unsubscribe(subscription)
            # A fired timer removes itself; a successful request still owns it.
            if response:
                GLib.source_remove(timer)

    try:
        created = request('CreateSession', '(a{sv})', (),
                          {'session_handle_token': GLib.Variant('s', 'session_'+uuid.uuid4().hex)})
        session = created['session_handle']
        print('Approve the VM monitor in the portal picker.', flush=True)
        request('SelectSources', '(oa{sv})', (session,),
                {'types': GLib.Variant('u', 1), 'multiple': GLib.Variant('b', False),
                 'cursor_mode': GLib.Variant('u', 2)})
        started = request('Start', '(osa{sv})', (session, ''), {})
        if not started.get('streams'):
            raise RuntimeError('Portal returned no PipeWire streams')
        node, properties = started['streams'][0]
        value, descriptors = bus.call_with_unix_fd_list_sync(
            destination, path, interface, 'OpenPipeWireRemote',
            GLib.Variant('(oa{sv})', (session, {})), GLib.VariantType.new('(h)'),
            Gio.DBusCallFlags.NONE, 10000, None, None)
        remote_fd = descriptors.get(value.unpack()[0])
        pipeline = Gst.parse_launch('pipewiresrc name=capture ! videoconvert ! '
                                    'video/x-raw,format=RGB ! appsink name=frames emit-signals=true sync=false')
        source = pipeline.get_by_name('capture')
        source.set_property('fd', remote_fd)
        if properties.get('pipewire-serial') and source.find_property('target-object'):
            source.set_property('target-object', str(properties['pipewire-serial']))
        else:
            source.set_property('path', str(node))
        loop = GLib.MainLoop()
        frames = []
        errors = []
        def sample_ready(sink):
            sample = sink.emit('pull-sample')
            info = GstVideo.VideoInfo.new_from_caps(sample.get_caps())
            buffer = sample.get_buffer()
            mapped, mapping = buffer.map(Gst.MapFlags.READ)
            if not mapped:
                errors.append('Cannot map captured frame')
                GLib.idle_add(loop.quit)
                return Gst.FlowReturn.ERROR
            try:
                raw = bytes(mapping.data)
                stride = info.stride[0]
                rgb = b''.join(raw[y*stride:y*stride+info.width*3] for y in range(info.height))
                frames.append((info.width, info.height, len(set(rgb))))
                if len(frames) == 3:
                    Path('portal-frame.ppm').write_bytes(
                        f'P6\n{info.width} {info.height}\n255\n'.encode()+rgb)
                    GLib.idle_add(loop.quit)
            finally:
                buffer.unmap(mapping)
            return Gst.FlowReturn.OK
        pipeline.get_by_name('frames').connect('new-sample', sample_ready)
        def pipeline_message(gst_bus, message):
            if message.type == Gst.MessageType.ERROR:
                errors.append(str(message.parse_error()[0]))
                loop.quit()
        gst_bus = pipeline.get_bus()
        gst_bus.add_signal_watch()
        gst_bus.connect('message', pipeline_message)
        timer = GLib.timeout_add_seconds(60, lambda: (loop.quit(), False)[1])
        pipeline.set_state(Gst.State.PLAYING)
        loop.run()
        if len(frames) >= 3 or errors:
            GLib.source_remove(timer)
        if errors or len(frames) < 3 or any(w <= 0 or h <= 0 or colors <= 16 for w, h, colors in frames[:3]):
            raise RuntimeError(f'Invalid capture: frames={frames[:3]}, errors={errors}')
        print('PASSED: three non-uniform RGB frames via approved portal/PipeWire:', frames[:3], flush=True)
    finally:
        if pipeline is not None:
            pipeline.set_state(Gst.State.NULL)
        if remote_fd is not None:
            os.close(remote_fd)
        if session is not None:
            bus.call_sync(destination, session, 'org.freedesktop.portal.Session', 'Close',
                          None, None, Gio.DBusCallFlags.NONE, 3000, None)


if __name__ == '__main__':
    main()
