#include <cstdint>
#include <functional>
#include <memory>
#include <stdexcept>
#include <string>
#include <vector>

#include "nav_msgs/msg/odometry.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/point_cloud2.hpp"
#include "tf2/LinearMath/Matrix3x3.h"
#include "tf2/LinearMath/Transform.h"
#include "tf2_geometry_msgs/tf2_geometry_msgs.hpp"
#include "tf2_ros/transform_broadcaster.h"

class FastlioBridge : public rclcpp::Node
{
public:
  FastlioBridge() : Node("fastlio_bridge")
  {
    world_frame_ = declare_parameter<std::string>("world_frame", "fastlio2new");
    const auto translation = declare_parameter<std::vector<double>>(
      "mapping.extrinsic_T", std::vector<double>{});
    const auto rotation = declare_parameter<std::vector<double>>(
      "mapping.extrinsic_R", std::vector<double>{});
    if (translation.size() != 3 || rotation.size() != 9) {
      throw std::invalid_argument("FAST-LIO IMU-to-LiDAR extrinsic is missing or invalid");
    }

    tf2::Quaternion q;
    tf2::Matrix3x3(
      rotation[0], rotation[1], rotation[2],
      rotation[3], rotation[4], rotation[5],
      rotation[6], rotation[7], rotation[8]).getRotation(q);
    imu_to_livox_.setOrigin(tf2::Vector3(translation[0], translation[1], translation[2]));
    imu_to_livox_.setRotation(q);

    cloud_pub_ = create_publisher<sensor_msgs::msg::PointCloud2>("/registered_scan", 5);
    odom_pub_ = create_publisher<nav_msgs::msg::Odometry>("/odom", 5);
    tf_broadcaster_ = std::make_unique<tf2_ros::TransformBroadcaster>(*this);
    cloud_sub_ = create_subscription<sensor_msgs::msg::PointCloud2>(
      "/cloud_registered", rclcpp::SensorDataQoS(),
      std::bind(&FastlioBridge::onCloud, this, std::placeholders::_1));
    odom_sub_ = create_subscription<nav_msgs::msg::Odometry>(
      "/Odometry", rclcpp::SensorDataQoS(),
      std::bind(&FastlioBridge::onOdometry, this, std::placeholders::_1));
  }

private:
  void onCloud(const sensor_msgs::msg::PointCloud2::ConstSharedPtr msg)
  {
    if (msg->header.frame_id != world_frame_) {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 2000, "Expected cloud in %s, got %s",
        world_frame_.c_str(), msg->header.frame_id.c_str());
      return;
    }
    auto out = *msg;
    out.header.frame_id = "odom";
    cloud_pub_->publish(out);
  }

  void onOdometry(const nav_msgs::msg::Odometry::ConstSharedPtr msg)
  {
    if (msg->header.frame_id != world_frame_ || msg->child_frame_id != "body") {
      RCLCPP_WARN_THROTTLE(
        get_logger(), *get_clock(), 2000, "Expected %s -> body odometry, got %s -> %s",
        world_frame_.c_str(), msg->header.frame_id.c_str(), msg->child_frame_id.c_str());
      return;
    }

    tf2::Transform world_to_imu;
    tf2::fromMsg(msg->pose.pose, world_to_imu);
    const tf2::Transform odom_to_base = world_to_imu * imu_to_livox_;

    nav_msgs::msg::Odometry out;
    out.header = msg->header;
    out.header.frame_id = "odom";
    out.child_frame_id = "base";
    const auto & position = odom_to_base.getOrigin();
    out.pose.pose.position.x = position.x();
    out.pose.pose.position.y = position.y();
    out.pose.pose.position.z = position.z();
    out.pose.pose.orientation = tf2::toMsg(odom_to_base.getRotation());

    const int64_t stamp_ns = rclcpp::Time(msg->header.stamp).nanoseconds();
    const double dt = (stamp_ns - previous_stamp_ns_) * 1e-9;
    if (has_previous_ && dt > 0.0) {
      const auto linear_odom =
        (odom_to_base.getOrigin() - previous_pose_.getOrigin()) / dt;
      const auto linear_base = odom_to_base.getRotation().inverse() * linear_odom;

      tf2::Quaternion delta =
        odom_to_base.getRotation() * previous_pose_.getRotation().inverse();
      delta.normalize();
      if (delta.w() < 0.0) {
        delta = tf2::Quaternion(-delta.x(), -delta.y(), -delta.z(), -delta.w());
      }
      const auto angular_odom = delta.getAxis() * delta.getAngle() / dt;
      const auto angular_base = odom_to_base.getRotation().inverse() * angular_odom;
      out.twist.twist.linear.x = linear_base.x();
      out.twist.twist.linear.y = linear_base.y();
      out.twist.twist.linear.z = linear_base.z();
      out.twist.twist.angular.x = angular_base.x();
      out.twist.twist.angular.y = angular_base.y();
      out.twist.twist.angular.z = angular_base.z();
    }
    previous_pose_ = odom_to_base;
    previous_stamp_ns_ = stamp_ns;
    has_previous_ = true;

    geometry_msgs::msg::TransformStamped transform;
    transform.header = out.header;
    transform.child_frame_id = "base";
    transform.transform = tf2::toMsg(odom_to_base);
    tf_broadcaster_->sendTransform(transform);
    odom_pub_->publish(out);
  }

  std::string world_frame_;
  tf2::Transform imu_to_livox_;
  tf2::Transform previous_pose_;
  int64_t previous_stamp_ns_ = 0;
  bool has_previous_ = false;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_sub_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr cloud_pub_;
  rclcpp::Publisher<nav_msgs::msg::Odometry>::SharedPtr odom_pub_;
  std::unique_ptr<tf2_ros::TransformBroadcaster> tf_broadcaster_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<FastlioBridge>());
  rclcpp::shutdown();
  return 0;
}
