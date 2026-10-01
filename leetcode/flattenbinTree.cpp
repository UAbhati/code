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
        void flatten(TreeNode* root) { # In worst case it can be O(n^2) because we are traversing the tree twice.
            if(!root) return;
            flatten(root->left);
            flatten(root->right);
            TreeNode* right = root->right;
            root->right = root->left;
            root->left = nullptr;
            TreeNode* curr = root;
            while(curr->right) {
                curr = curr->right;
            }
            curr->right = right;
        }
    };

# This is a better solution because it is O(n) time complexity and O(1) space complexity.
 class Solution {
    public:
        TreeNode* prev = nullptr;
        void flatten(TreeNode* root) {
            if(!root) return;
            flatten(root->right);
            flatten(root->left);
            root->right = prev;
            root->left = nullptr;

            prev = root;
        }
    };