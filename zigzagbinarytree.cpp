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
        vector<vector<int>> zigzagLevelOrder(TreeNode* root) {
            vector<vector<int>> v;
            if(!root) return v;
            queue<TreeNode*> q;
            q.push(root);
            bool right = false;
            while(!q.empty()) {
                int s = q.size();
                vector<int> level;
                while(s--) {
                    TreeNode* node = q.front();
                    q.pop();
                    level.push_back(node->val);
                    if(node->left) {
                        q.push(node->left);
                    }
                    if(node->right) {
                        q.push(node->right);
                    }
                }
                if(right) {
                    right = false;
                    reverse(level.begin(),level.end());
                    v.push_back(level);
                } else {
                    v.push_back(level);
                    right = true;
                }
            }
            return v;
        }
    };