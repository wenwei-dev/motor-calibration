if __name__ == '__main__':
    import sys
    sys.path.insert(0, '/opt/hansonrobotics/ros/lib/python2.7/dist-packages')
    import rospy
    from blender_api_msgs.msg import CurrentFrame
    def callback(msg):
        print '{},{}'.format(msg.name, msg.frame)
        sys.stdout.flush()
    rospy.init_node('read_frame_info')
    rospy.Subscriber('/blender_api/get_current_frame', CurrentFrame, callback)
    rospy.spin()
