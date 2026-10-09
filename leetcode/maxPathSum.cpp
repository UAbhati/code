/**
 * Definition for a binary tree node.
 * struct TreeNode {
 *     int val;
 *     TreeNode *left;
 *     TreeNode *right;
 *     TreeNode() : val(0), left(nullptr), right(nullptr) {}
 *     TreeNode(int x) : val(x), left(nullptr), right(nullptr) {}
 *     TreeNode(int x, TreeNode *left, TreeNode *right) : val(x), left(left), right(right) {}
 * };
 */
 class Solution {
    public:
        int ans = INT_MIN;
        int dfs(TreeNode* node) {
            if (node == nullptr) return 0;
            int leftGain = max(0,dfs(node->left));
            int rightGain = max(0,dfs(node->right));

            int pathSum = node-> val + leftGain + rightGain;
            ans = max(ans, pathSum);
            return node->val + max(leftGain, rightGain);
        }
        int maxPathSum(TreeNode* root) {
            dfs(root);
            return ans;
        }
    };