"""
Gym environment for training residual policies 
on top of rmp2 policies for xarm7 robot
"""

from rmp2.envs.xarm7_env import Xarm7Env
from rmp2.rmpgraph.robotics import RobotRMPGraph
from rmp2.utils.python_utils import merge_dicts
import tensorflow as tf
import numpy as np
import os

DEFAULT_CONFIG = {
    "dtype": "float32",
    "offset": 1e-3,
}

class Xarm7ResidualEnv(Xarm7Env):
    """
    Gym environment for training residual policies 
    on top of rmp2 policies for xarm7 robot
    """
    def __init__(self, config=None):
        if config is not None:
            config = merge_dicts(DEFAULT_CONFIG, config)
        else:
            config = DEFAULT_CONFIG.copy()

        # load rmp configs for the rmp2 policy
        config_path = os.path.join(
            os.path.dirname(__file__), 
            '../configs/xarm7_residual_config.yaml'
            )

        # create rmp2 policy
        self.rmp_graph = RobotRMPGraph(
            'xarm7',
            config_path=config_path, 
            dtype=config['dtype'], 
            offset=config['offset'])

        self.dtype = config['dtype']
        self._ts_goal = None
        self._ts_obs = None

        super().__init__(config=config)

    def _generate_random_goal(self):
        # additionally keep a goal tensor for computing rmp2 policy
        current_goal, goal_uid = super()._generate_random_goal()
        self._ts_goal = tf.convert_to_tensor(np.array([current_goal]), dtype=self.dtype)
        return current_goal, goal_uid

    def _generate_random_obstacles(self):
        # additionally keep a obstacle tensor for computing rmp2 policy
        current_obs, obs_uids = super()._generate_random_obstacles()
        self._ts_obs = tf.convert_to_tensor(np.array([current_obs]), dtype=self.dtype)
        self._ts_obs = tf.reshape(self._ts_obs, (1, -1, self.workspace_dim + 1))
        return current_obs, obs_uids

    def step(self, residual_action):
        # compute the rmp2 policy
        joint_poses, joint_vels, _ = self._robot.get_observation()
        ts_joint_poses = tf.convert_to_tensor([joint_poses], dtype=self.dtype)
        ts_joint_vels = tf.convert_to_tensor([joint_vels], dtype=self.dtype)
        ts_action = self.rmp_graph(ts_joint_poses, ts_joint_vels, obstacles=self._ts_obs, goal=self._ts_goal)
        action = ts_action.numpy()
        action = action.flatten()
        action = np.clip(action, self._action_space.low, self._action_space.high)
        # add the residual policy and rmp2 policy together
        action = action + residual_action
        return super().step(action)
