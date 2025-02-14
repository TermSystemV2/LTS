/*
 Navicat Premium Data Transfer

 Source Server         : 本地数据库
 Source Server Type    : MySQL
 Source Server Version : 80026
 Source Host           : localhost:3306
 Source Schema         : studentscore

 Target Server Type    : MySQL
 Target Server Version : 80026
 File Encoding         : 65001

 Date: 10/12/2022 23:14:27
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for excellentstudyclass
-- ----------------------------
DROP TABLE IF EXISTS `excellentstudyclass`;
CREATE TABLE `excellentstudyclass`  (
  `grade` int(0) NOT NULL,
  `year` int(0) NOT NULL,
  `totalClassNum` int(0) NULL DEFAULT NULL,
  `excellentClassNum` int(0) NULL DEFAULT NULL,
  PRIMARY KEY (`grade`, `year`) USING BTREE
) ENGINE = InnoDB CHARACTER SET = utf8 COLLATE = utf8_general_ci ROW_FORMAT = Dynamic;

-- ----------------------------
-- Records of excellentstudyclass
-- ----------------------------
INSERT INTO `excellentstudyclass` VALUES (15, 2016, 47, 12);
INSERT INTO `excellentstudyclass` VALUES (15, 2018, 0, 1);
INSERT INTO `excellentstudyclass` VALUES (16, 2017, 14, 12);
INSERT INTO `excellentstudyclass` VALUES (16, 2018, 36, 15);
INSERT INTO `excellentstudyclass` VALUES (16, 2019, 14, 12);
INSERT INTO `excellentstudyclass` VALUES (17, 2018, 12, 11);
INSERT INTO `excellentstudyclass` VALUES (17, 2019, 12, 9);
INSERT INTO `excellentstudyclass` VALUES (17, 2020, 12, 11);
INSERT INTO `excellentstudyclass` VALUES (18, 2019, 14, 13);
INSERT INTO `excellentstudyclass` VALUES (18, 2020, 14, 6);
INSERT INTO `excellentstudyclass` VALUES (18, 2021, 14, 7);
INSERT INTO `excellentstudyclass` VALUES (19, 2020, 13, 11);
INSERT INTO `excellentstudyclass` VALUES (19, 2021, 13, 7);
INSERT INTO `excellentstudyclass` VALUES (20, 2021, 14, 13);

SET FOREIGN_KEY_CHECKS = 1;
