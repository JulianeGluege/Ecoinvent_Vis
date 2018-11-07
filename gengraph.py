import sys
import os
import pandas as pd
import numpy as np
import xml.dom.minidom as minidom  # package to read XML Documents
import graphviz as gr  # python API to graphViz


# helper functions ################################
def sum_amounts(product_df):
    """
    Function to sum up the amounts / volumes for products with same name
    :param product_df: dataframe with cols name, amount, (volume), unit
    :return: summed_product_df
    """

    summed_product_df = pd.DataFrame(columns=product_df.columns.values)
    product_names = product_df['product name'].unique()  # get product names

    # check if product_df has a volume column
    if product_df.shape[1] > 3:
        has_volume = True
    else:
        has_volume = False

    for p in product_names:
        act_product_df = product_df[product_df['product name'] == p]
        actual_unit = act_product_df['unit'].values[0]  # store unit of current product
        if act_product_df.shape[0] > 1:  # check if there is more than one row for current product
            summed_amount = act_product_df['amount'].sum()
            if has_volume:
                summed_volume = act_product_df['volume'].sum()
                summed_product_df = summed_product_df.append(
                    {'product name': p, 'amount': summed_amount, 'volume': summed_volume, 'unit': actual_unit},
                    ignore_index=True)
            else:  # no volume in product_df
                summed_product_df = summed_product_df.append(
                    {'product name': p, 'amount': summed_amount, 'unit': actual_unit}, ignore_index=True)
        else:
            summed_product_df = summed_product_df.append(act_product_df, ignore_index=True)

    return summed_product_df


def format_float_to_string(x):
    """
    Function to format a given float to 4 digits
    :param x: float e.g 0.345799999
    :return: string of the float with 4 digits e.g. '0.3458'
    """
    return format(x, '.4g')


def get_node_names(df, n_max_rows):
    """
    Function to create node names from the entries in the dataframe with in-/outputs
    :param df: dataframe with inputs / outputs
    :param n_max_rows: maximal number of rows (for this in- or output) which should be plotted at the end
    :return names_list: list with strings of in- or outputs
    """

    names_list = []
    df['amount'] = df['amount'].apply(format_float_to_string)  # apply the function to amount in the dataframe
    df.reset_index(drop=True)  # reset index
    number = df.shape[0]
    if number > 0:  # are there any in- or outputs in the dataframe
        if number > n_max_rows:
            number = n_max_rows
        for elem in np.arange(0, number):
            name = df.loc[[elem], ['amount']].values[0][0] + ' ' + df.loc[[elem], ['unit']].values[0][0] + ' of ' + \
                   df.loc[[elem], ['product name']].values[0][0]  # build string (e.g. 3 kg of pentane)
            names_list.append(name)  # add string to list

    return names_list  # list with strings


def create_graph(names_input_e, names_input_t, names_output_e, names_byproduct, name_referenceproduct,
                 activity_geoshort_name):
    """
    Function to create a graphViz graph given the lists of node names for in-/output from/to environment and technosphere
    :param names_input_e: list of node names of inputs from environment
    :param names_input_t: list of node names of inputs from technosphere
    :param names_output_e: list of node names of outputs to environment
    :param names_byproduct: list of node names of outputs to technosphere (byproduct)
    :param name_referenceproduct: node name of the reference product (string)
    :param activity_geoshort_name: node name for the activity (string)
    :return: graph (graphviz object)
    """

    # create element for dot language
    graph = gr.Digraph(comment='', format='pdf')
    graph.graph_attr.update(rankdir='LR')  # general order of nodes from left to right

    # create subgraphs left, center, right + corresponding edges
    # create subgraph in the center
    with graph.subgraph(name='center') as c:
        c.graph_attr.update(rank='same')  # set all nodes to same rank
        # create activity node
        c.node('Activity', activity_geoshort_name, shape='box', color='white', fillcolor='lightsteelblue', style='filled')

        # create inputs from environment nodes + edges to activity node
        for i, name in enumerate(names_input_e):
            c.node('InputE_' + str(i), name, shape='box', color='white', fillcolor='snow', style='filled')  # node
            graph.edge('Activity', 'InputE_' + str(i),
                       dir='back')  # edge to activity (edge is defined inverse, such that the input nodes appear _below_ the product node)

        # create outputs to environment nodes + edges from activity node
        for i, name in enumerate(names_output_e):
            c.node('OutputE_' + str(i), name, shape='box', color='white', fillcolor='snow', style='filled')
            graph.edge('OutputE_' + str(i), 'Activity',
                       dir='back')  # edge to activity (edge is defined inverse, such that the output nodes appear _above_ the product node)

    # create subgraph on the left (inputs from technosphere)
    with graph.subgraph(name='input_technosphere') as it:
        it.graph_attr.update(rank='min')  # set all nodes to minimum rank -> left
        for i, name in enumerate(names_input_t):
            it.node('InputT_' + str(i), name, shape='box', color='white', fillcolor='ghostwhite', style='filled')  # node
            graph.edge('InputT_' + str(i), 'Activity')  # edge to activity

    # create subgraph on the right (ref. product and byproducts)
    with graph.subgraph(name='product_subgraph') as p:
        p.graph_attr.update(rank='max')  # set all nodes to max rank -> right
        p.node('Product', name_referenceproduct, shape='box', color='white', fillcolor='ghostwhite', style='filled')  # ref. product node
        graph.edge('Activity', 'Product')  # edge activits to product

        # output of by products
        for i, name in enumerate(names_byproduct):
            p.node('OutputT_' + str(i), name, shape='box', color='white', fillcolor='ghostwhite', style='filled')  # node
            graph.edge('Activity', 'OutputT_' + str(i))  # edge

    return graph


################################

# start main program
# print('Start processing')
# read arguments
# print('Number of arguments:' + str(len(sys.argv)) + ' arguments.')
# print('Argument List: ' + str(sys.argv))

# get first command line argument
raw_data_path = sys.argv[1]
print('Got path to raw data: ' + raw_data_path)
files_to_process = os.listdir(raw_data_path)
# print('Found the following files: ' + str(files_to_process))

output_dir = raw_data_path + '/' + 'output'  # set output dir

# loop through files and generate graphs
for file in files_to_process:
    print('Processing file: ' + file, end='\t')  # no new line at the end but a tab
    try:
        # parse file, create tree structure and obtain the root element (document object model)
        dom = minidom.parse(raw_data_path + '/' + file)

        activity_name = dom.getElementsByTagName('activityName')[0].firstChild.nodeValue  # get name of activity
        geo_short_name = dom.getElementsByTagName('shortname')[0].firstChild.nodeValue  # get geo short location

        # collect input from technosphere
        inputT_df = pd.DataFrame(columns=['product name', 'amount', 'unit'])
        intermediate_exchange = dom.getElementsByTagName('intermediateExchange')
        for element in intermediate_exchange:
            # find all entries in name.inputGroup which are 5 and write the results in a table
            input_group = element.getElementsByTagName('inputGroup')  # select element 'inputGroup'
            if len(input_group) > 0:  # check if there actually was an element called 'inputGroup'
                if (int(input_group[0].firstChild.nodeValue)) == 5:  # check for nodeValue 5 -> input from technosphere
                    act_product_name = element.getElementsByTagName('name')[
                        0].firstChild.nodeValue  # select product name
                    act_unit = element.getElementsByTagName('unitName')[0].firstChild.nodeValue  # unit
                    act_amount = element.getAttribute('amount')  # amount
                    inputT_df = inputT_df.append(
                        {'product name': act_product_name, 'amount': act_amount, 'unit': act_unit},
                        ignore_index=True)  # append result to table

        inputT_df['amount'] = inputT_df['amount'].astype(float)  # convert string to float for amount

        # collect output to technosphere (byproduct + reference product)
        outputT_byproduct_df = pd.DataFrame(columns=['product name', 'amount', 'volume', 'unit'])
        outputT_referenceproduct_df = pd.DataFrame(columns=['product name', 'amount', 'volume', 'unit'])
        intermediate_exchange = dom.getElementsByTagName('intermediateExchange')
        for element in intermediate_exchange:
            # find all entries in name.outputGroup which are 0 (or 2) and write the results in tables
            output_group = element.getElementsByTagName('outputGroup')  # select element 'outputGroup'
            if len(output_group) > 0:  # check if there actually was an element called 'outputGroup'

                if (int(output_group[0].firstChild.nodeValue)) == 2:  # check for nodeValue 2 -> byproduct
                    act_product_name = element.getElementsByTagName('name')[
                        0].firstChild.nodeValue  # select product name
                    act_unit = element.getElementsByTagName('unitName')[0].firstChild.nodeValue  # unit
                    act_amount = element.getAttribute('amount')  # amount
                    act_volume = element.getAttribute('productionVolumeAmount')
                    outputT_byproduct_df = outputT_byproduct_df.append(
                        {'product name': act_product_name, 'amount': act_amount, 'volume': act_volume,
                         'unit': act_unit}, ignore_index=True)  # append result to table

                if (int(output_group[0].firstChild.nodeValue)) == 0:  # check for nodeValue 0 -> reference product
                    act_product_name = element.getElementsByTagName('name')[
                        0].firstChild.nodeValue  # select product name
                    act_unit = element.getElementsByTagName('unitName')[0].firstChild.nodeValue  # unit
                    act_amount = element.getAttribute('amount')  # amount
                    act_volume = element.getAttribute('productionVolumeAmount')
                    outputT_referenceproduct_df = outputT_referenceproduct_df.append(
                        {'product name': act_product_name, 'amount': act_amount, 'volume': act_volume,
                         'unit': act_unit}, ignore_index=True)  # append result to table

        outputT_referenceproduct_df[['amount', 'volume']] = outputT_referenceproduct_df[['amount', 'volume']].astype(
            float)  # convert string to float for volume
        outputT_byproduct_df[['amount', 'volume']] = outputT_byproduct_df[['amount', 'volume']].astype(
            float)  # convert string to float for amount

        # collect input from environment
        inputE_df = pd.DataFrame(columns=['product name', 'amount', 'unit'])
        elementary_exchange = dom.getElementsByTagName('elementaryExchange')
        for element in elementary_exchange:
            # find all entries in name.inputGroup which are 4 and write the results in a table
            input_group = element.getElementsByTagName('inputGroup')  # select element 'inputGroup'
            if len(input_group) > 0:  # check if there actually was an element called 'inputGroup'
                if (int(input_group[0].firstChild.nodeValue)) == 4:  # check for nodeValue 4 -> input from environment
                    act_product_name = element.getElementsByTagName('name')[0].firstChild.nodeValue
                    act_unit = element.getElementsByTagName('unitName')[0].firstChild.nodeValue
                    act_amount = element.getAttribute('amount')
                    inputE_df = inputE_df.append(
                        {'product name': act_product_name, 'amount': act_amount, 'unit': act_unit}, ignore_index=True)

        inputE_df['amount'] = inputE_df['amount'].astype(float)  # convert string to float for amount

        # collect output to environment
        outputE_df = pd.DataFrame(columns=['product name', 'amount', 'unit'])
        elementary_exchange = dom.getElementsByTagName('elementaryExchange')
        for element in elementary_exchange:
            # find all entries in name.outputGroup which are 4 and write the results in a table
            output_group = element.getElementsByTagName('outputGroup')  # select element 'outputGroup'
            if len(output_group) > 0:  # check if there actually was an element called 'outputGroup'
                if (int(output_group[0].firstChild.nodeValue)) == 4:  # check for nodeValue 4 -> output to environment
                    act_product_name = element.getElementsByTagName('name')[0].firstChild.nodeValue
                    act_unit = element.getElementsByTagName('unitName')[0].firstChild.nodeValue
                    act_amount = element.getAttribute('amount')
                    outputE_df = outputE_df.append(
                        {'product name': act_product_name, 'amount': act_amount, 'unit': act_unit}, ignore_index=True)

        outputE_df['amount'] = outputE_df['amount'].astype(float)  # convert string to float for amount

        # sum up the amounts / volumes for products with the same name (uses a self-defined function)
        inputT_df = sum_amounts(inputT_df)
        inputE_df = sum_amounts(inputE_df)
        outputE_df = sum_amounts(outputE_df)
        outputT_referenceproduct_df = sum_amounts(outputT_referenceproduct_df)
        outputT_byproduct_df = sum_amounts(outputT_byproduct_df)

        # sort products by amount / volume ... the different units are not considered!
        outputT_byproduct_df = outputT_byproduct_df.sort_values('volume', ascending=False)
        outputE_df = outputE_df.sort_values('amount', ascending=False)
        inputE_df = inputE_df.sort_values('amount', ascending=False)
        inputT_df = inputT_df.sort_values('amount', ascending=False)

        # make string for activity
        activity_geoshort_name = activity_name + '\n' + geo_short_name  # combine string of activity name and geo short name

        # make strings for the in- and outputs, use self-defined function get_node_names
        names_input_t = get_node_names(inputT_df, 5)
        names_byproduct = get_node_names(outputT_byproduct_df, 4)
        name_referenceproduct = get_node_names(outputT_referenceproduct_df, 1)
        names_input_e = get_node_names(inputE_df, 5)
        names_output_e = get_node_names(outputE_df, 5)

        graph = create_graph(names_input_e, names_input_t, names_output_e, names_byproduct, name_referenceproduct[0],
                             activity_geoshort_name)

        # write graph to file
        act_filename = file.split(sep='.')[0]  # get filename without ending
        if not os.path.exists(output_dir):  # generate output dir if it doesn't exist
            os.mkdir(output_dir)

        # write graph to file
        graph.render(output_dir + '/' + act_filename + '.gv', view=False)
        print('done...')

    except:  # catch *all* exceptions
        print('[WARNING] could not parse XML structure, skipping file...')

print('Results can be found in: ' + output_dir + '/')
