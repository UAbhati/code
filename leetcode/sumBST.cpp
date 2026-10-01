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
        struct info {
            int mini;
            int maxi;
            bool isBST;
            int sum;
        };

        info dfs(TreeNode* root, int& ans) {
            if(!root) {
                return {INT_MAX, INT_MIN, true, 0};
            };
            info left = dfs(root->left, ans);
            info right = dfs(root->right, ans);
            if(
                left.isBST && right.isBST && left.maxi < root->val && right.mini > root->val
            ) {
                int sum = left.sum + right.sum + root->val;
                ans = max(ans,sum);
                return {
                    min(left.mini, root->val),
                    max(right.maxi, root-> val),
                    true,
                    sum
                };
            };
            return {
                0,
                0,
                false,
                0
            };
        }

        int maxSumBST(TreeNode* root) {
            int ans = 0;
            dfs(root, ans);
            return ans;
        }
    };