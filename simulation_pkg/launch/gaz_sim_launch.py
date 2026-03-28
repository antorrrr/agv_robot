import os
from ament_index_python.packages import get_package_share_directory
from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration, Command
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch_ros.actions import Node
import launch_ros.descriptions
from launch_ros.parameter_descriptions import ParameterValue
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    package_name = 'simulation_pkg'

    # Check if we're told to use sim time
    use_sim_time = LaunchConfiguration('use_sim_time')

    # Get the urdf/xacro file path
    pkg_share = get_package_share_directory(package_name)
    path_to_urdf = get_package_share_path(package_name) /'description'/'robot_urdf.xacro'


    gz_resource_path = SetEnvironmentVariable(
    name='GZ_SIM_RESOURCE_PATH',
    value=':'.join([
        pkg_share,
        os.path.join(pkg_share, 'models')
    ])
)

    # Create a robot_state_publisher node
    rsp = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory(package_name),'launch','rsp_launch.py'
                )]), launch_arguments={'use_sim_time': 'true', 'use_ros2_control': 'true'}.items()
    )

    # Gazebo Fortress world
    world = os.path.join(
        get_package_share_directory(package_name),
        'worlds',
        'industrial-warehouse.sdf'
    )

    gz_sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('ros_gz_sim'),
                'launch',
                'gz_sim.launch.py'
            )
        ),
        launch_arguments={
            'gz_args': f'-r {world}',
            'on_exit_shutdown': 'true'
        }.items(),
    )

    # Bridge gazebo parameters with ROS
    bridge_params = os.path.join(
    get_package_share_directory(package_name),
        'config',
        'gz_bridge.yaml'
    )

    ros_gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '--ros-args',
            '-p',
            f'config_file:={bridge_params}',
        ],
        output='screen',
    )

    ros_gz_image_bridge = Node(
        package='ros_gz_image',
        executable='image_bridge',
        arguments=["/camera/image_raw"]
    )

    # Spawn the robot in Gazebo
    spawn_entity = Node(
        package="ros_gz_sim",
        executable="create",
        arguments=[
            "-name",
            "agv_robot",
            "-topic",
            "/robot_description",
            "-x",
            "0",
            "-y",
            "0",
            "-z",
            "1.4",
        ],
        output="screen",
    )

    # Run ros2 control spawner scripts
    joint_state_broadcaster_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        output='screen',
    )

    diff_controller_spawner = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_controller'],
        output='screen',
    )

    twist_mux_params = os.path.join(get_package_share_directory('simulation_pkg'), 'config', 'twist_mux.yaml')
    twist_mux = Node(
        package='twist_mux',
        executable='twist_mux',
        parameters=[twist_mux_params, {'use_sim_time': True}],
        remappings=[('/cmd_vel_out', 'diff_controller/cmd_vel_unstamped')]
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use sim time if true'
        ),
        gz_resource_path,
        rsp,
        gz_sim,
        spawn_entity,
        ros_gz_bridge,
        ros_gz_image_bridge,
        joint_state_broadcaster_spawner,
        diff_controller_spawner,
        twist_mux
    ])
