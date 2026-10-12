#include "sensor_scan_generation/sensor_scan_generation.hpp"

namespace sensor_scan_generation
{

SensorScanGeneration::SensorScanGeneration(const rclcpp::NodeOptions & options)
: Node("sensor_scan_generation", options){

    lidar_frame_ = this->declare_parameter<std::string>("lidar_frame", "livox_frame");
    base_footprint_frame_ = this->declare_parameter<std::string>("base_footprint_frame", "base_footprint");

    tf_buffer_ = std::make_unique<tf2_ros::Buffer>(this->get_clock());
    tf_listener_ = std::make_unique<tf2_ros::TransformListener>(*tf_buffer_);
    br_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);

    pub_laser_cloud_ = this->create_publisher<sensor_msgs::msg::PointCloud2>("/lidar_frame_pcd", 2);
    // pub_base_footprint_odometry_ = this->create_publisher<nav_msgs::msg::Odometry>("/base_footprint_odometry", 2);
    pub_base_footprint_odometry_ = this->create_publisher<nav_msgs::msg::Odometry>("/odom", 2);

    rmw_qos_profile_t qos_profile = {
        RMW_QOS_POLICY_HISTORY_KEEP_LAST,
        1,
        RMW_QOS_POLICY_RELIABILITY_BEST_EFFORT,
        RMW_QOS_POLICY_DURABILITY_VOLATILE,
        RMW_QOS_DEADLINE_DEFAULT,
        RMW_QOS_LIFESPAN_DEFAULT,
        RMW_QOS_POLICY_LIVELINESS_SYSTEM_DEFAULT,
        RMW_QOS_LIVELINESS_LEASE_DURATION_DEFAULT,
        false};

    laser_cloud_sub_.subscribe(this, "/registered_scan", qos_profile);
    odometry_sub_.subscribe(this, "/registered_odometry", qos_profile);

    sync_ = std::make_unique<message_filters::Synchronizer<SyncPolicy>>(
        SyncPolicy(100), odometry_sub_, laser_cloud_sub_);
    sync_->registerCallback(std::bind(
        &SensorScanGeneration::laserCloudAndOdometryHandler, this, std::placeholders::_1,
        std::placeholders::_2));

    RCLCPP_INFO(this->get_logger(), MAG "SensorScanGeneration node is START" RST);

}

SensorScanGeneration::~SensorScanGeneration()
{
    RCLCPP_INFO(this->get_logger(), MAG "SensorScanGeneration node is OVER" RST);
}

/**
 * @brief 获取 odom 和 lidar_frame 之间的变换;
 *        获取 lidar_frame 和 base_footprint 之间的变换;
 *        计算 odom 和 base_footprint 之间的变换;
 * 
 *        发布 odom 和 base_footprint 之间的变换;
 *        
 */
void SensorScanGeneration::laserCloudAndOdometryHandler(
    const nav_msgs::msg::Odometry::ConstSharedPtr & odometry_msg,
    const sensor_msgs::msg::PointCloud2::ConstSharedPtr & pcd_msg)
{
    tf2::Transform tf_odom_to_base_footprint_;
    tf2::Transform tf_odom_to_lidar;

    tf2::fromMsg(odometry_msg->pose.pose, tf_odom_to_lidar);
    tf2::Transform tf_lidar_to_base_footprint;
    try {
      const auto transform = tf_buffer_->lookupTransform(
        lidar_frame_, base_footprint_frame_, rclcpp::Time(pcd_msg->header.stamp),
        rclcpp::Duration::from_seconds(0.5));
      tf2::fromMsg(transform.transform, tf_lidar_to_base_footprint);
    } catch (const tf2::TransformException & ex) {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 2000, "Missing lidar-to-base TF; skipping frame: %s", ex.what());
      return;
    }
    tf_odom_to_base_footprint_ = tf_odom_to_lidar * tf_lidar_to_base_footprint;

    publishTransform(
    tf_odom_to_base_footprint_, odometry_msg->header.frame_id, base_footprint_frame_, pcd_msg->header.stamp);
    publishOdometry(
    tf_odom_to_base_footprint_, odometry_msg->header.frame_id, base_footprint_frame_, pcd_msg->header.stamp);

    sensor_msgs::msg::PointCloud2 out;
    pcl_ros::transformPointCloud(lidar_frame_, tf_odom_to_lidar.inverse(), *pcd_msg, out);
    pub_laser_cloud_->publish(out);
}

void SensorScanGeneration::publishTransform(
  const tf2::Transform & transform, const std::string & parent_frame,
  const std::string & child_frame, const rclcpp::Time & stamp)
{
  geometry_msgs::msg::TransformStamped transform_msg;
  transform_msg.header.stamp = stamp;
  transform_msg.header.frame_id = parent_frame;
  transform_msg.child_frame_id = child_frame;
  transform_msg.transform = tf2::toMsg(transform);
  br_->sendTransform(transform_msg);
}

void SensorScanGeneration::publishOdometry(
  const tf2::Transform & transform, std::string parent_frame, const std::string & child_frame,
  const rclcpp::Time & stamp)
{
  nav_msgs::msg::Odometry out;
  out.header.stamp = stamp;
  out.header.frame_id = parent_frame;
  out.child_frame_id = child_frame;

  const auto & origin = transform.getOrigin();
  out.pose.pose.position.x = origin.x();
  out.pose.pose.position.y = origin.y();
  out.pose.pose.position.z = origin.z();
  out.pose.pose.orientation = tf2::toMsg(transform.getRotation());

  const int64_t stamp_ns = stamp.nanoseconds();
  const double dt = (stamp_ns - previous_stamp_ns_) * 1e-9;

  if (has_previous_odometry_ && dt > 0.0) {
    const auto velocity_odom =
      (transform.getOrigin() - previous_transform_.getOrigin()) / dt;
    const auto velocity_base = transform.getRotation().inverse() * velocity_odom;

    tf2::Quaternion rotation_delta =
      transform.getRotation() * previous_transform_.getRotation().inverse();
    rotation_delta.normalize();
    if (rotation_delta.w() < 0.0) {
      rotation_delta = tf2::Quaternion(
        -rotation_delta.x(), -rotation_delta.y(),
        -rotation_delta.z(), -rotation_delta.w());
    }
    const auto angular_odom = rotation_delta.getAxis() * rotation_delta.getAngle() / dt;
    const auto angular_base = transform.getRotation().inverse() * angular_odom;

    out.twist.twist.linear.x = velocity_base.x();
    out.twist.twist.linear.y = velocity_base.y();
    out.twist.twist.linear.z = velocity_base.z();
    out.twist.twist.angular.x = angular_base.x();
    out.twist.twist.angular.y = angular_base.y();
    out.twist.twist.angular.z = angular_base.z();
  }

  previous_transform_ = transform;
  previous_stamp_ns_ = stamp_ns;
  has_previous_odometry_ = true;

  pub_base_footprint_odometry_->publish(out);
}

}   // namespace sensor_scan_generation

#include "rclcpp_components/register_node_macro.hpp"
RCLCPP_COMPONENTS_REGISTER_NODE(sensor_scan_generation::SensorScanGeneration)
