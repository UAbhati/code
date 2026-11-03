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
 // BFS solution extra space
 class Solution {
    public:
        vector<int> rightSideView(TreeNode* root) {
            vector<int> ans;
            if(!root) return ans;
            queue<TreeNode*> q;
            q.push(root);
            while(!q.empty()) {
                int n = q.size();
                for(int i=0;i<n;i++) {
                    TreeNode* node = q.front();
                    q.pop();
                    if(i== n-1) {
                        ans.push_back(node->val);
                    }
                    if(node->left) {
                        q.push(node->left);
                    }
                    if(node->right) {
                        q.push(node->right);
                    }
                }
            }
            return ans;
        }
    };

// DFS solution without extra space

class Solution {
    public:
        vector<int> ans;

        void dfs(TreeNode* root, int depth) {
            if (!root) return;

            // First node encountered at this depth
            if (depth == ans.size()) {
                ans.push_back(root->val);
            }

            // Prioritize right subtree
            dfs(root->right, depth + 1);
            dfs(root->left, depth + 1);
        }

        vector<int> rightSideView(TreeNode* root) {
            dfs(root, 0);
            return ans;
        }
    };
