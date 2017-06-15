SHAPE_KEYS = ['Basis', 'Shrinkwrap', 'adjustments', 'brow_center_UP', 'brow_center_DN', 'brow_inner_UP.L', 'brow_inner_DN.L', 'brow_inner_UP.R', 'brow_inner_DN.R', 'brow_outer_UP.L', 'brow_outer_DN.L', 'brow_outer_UP.R', 'brow_outer_DN.R', 'eye-flare.UP.L', 'eye-blink.UP.L', 'eye-flare.UP.R', 'eye-blink.UP.R', 'eye-blink.LO.L', 'eye-flare.LO.L', 'eye-blink.LO.R', 'eye-flare.LO.R', 'wince.L', 'wince.R', 'sneer.L', 'sneer.R', 'eyes-look.dn', 'eyes-look.up', 'lip-UP.C.UP', 'lip-UP.C.DN', 'lip-UP.L.UP', 'lip-UP.L.DN', 'lip-UP.R.UP', 'lip-UP.R.DN', 'lips-smile.L', 'lips-smile.R', 'lips-wide.L', 'lips-narrow.L', 'lips-wide.R', 'lips-narrow.R', 'lip-DN.C.DN', 'lip-DN.C.UP', 'lip-DN.L.DN', 'lip-DN.L.UP', 'lip-DN.R.DN', 'lip-DN.R.UP', 'lips-frown.L', 'lips-frown.R', 'lip-JAW.DN', 'jaw']

if __name__ == '__main__':
    import sys
    sys.path.insert(0, '/opt/hansonrobotics/ros/lib/python2.7/dist-packages')
    import rospy
    from pau2motors.msg import pau
    def callback(msg):
        print msg.m_coeffs
        sys.stdout.flush()
    rospy.init_node('read_shapekeys')
    rospy.Subscriber('/blender_api/get_pau', pau, callback)
    rospy.spin()
